import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.production_line.production_line import get_all_child_lines
from erpnext.manufacturing.doctype.slab.api import get_slabs_for
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_quality_report.api import create_slab_quality_report
from erpnext.manufacturing.doctype.slab_quality_report.slab_quality_report import SlabQualityReport
from erpnext.manufacturing.page.operator_station.operator_station import (
	finish_process,
	get_top_job_card_for_process,
	start_process,
)
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.warehouse.constants import (
	PREMIUM_WAREHOUSE,
	REJECTED_WAREHOUSE,
	STANDARD_WAREHOUSE,
)


@frappe.whitelist()
def start_qa_process(slab_number: str):
	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]
	#    1. Get the job card for quality analysis on the given line.
	job_card_result = get_top_job_card_for_process("Quality Check", slab.line, True)
	job_card: JobCard = job_card_result.get("top_job_card")  # pyright: ignore[reportAssignmentType]
	if not job_card:
		frappe.throw("No Job Card found")
	job_card_name = job_card.name
	#    2. Start the job card.
	#    3. Move the slab to quality check.
	start_process(
		job_card_name, slab_name=slab.name or "", slab_template=slab.template, process_name="Quality Check"
	)

	#    4. Return the job card number.
	return job_card_name


@frappe.whitelist()
def submit_qa_report(report: str | dict, shift: str, job_card: str, slab_number: str):
	try:
		frappe.db.begin()

		if isinstance(report, str):
			report = frappe.parse_json(report)
		slab_grade: str | None = report.get("grade")  # pyright: ignore[reportAttributeAccessIssue]

		slab_qc: SlabQualityReport = frappe.new_doc("Slab Quality Report")  # pyright: ignore[reportAssignmentType]
		slab_qc.update(report)
		slab_qc.shift = shift

		# 1. Create the slab quality report.
		create_slab_quality_report(slab_number, slab_qc)
		# Then,
		finish_qc_process(slab_number, slab_grade, job_card)

		frappe.db.commit()

		return {"slab": slab_number, "job_card": job_card}

	except Exception:
		frappe.db.rollback()
		raise


@frappe.whitelist()
def get_slab_or_jobcard_for_qa(line: str, job_card_number: str | None = None):
	job_card: JobCard | None = None
	if job_card_number:
		job_card = frappe.get_doc("Job Card", job_card_number)  # pyright: ignore[reportAssignmentType]

	child_lines = get_all_child_lines(line)
	job_card_data = get_top_job_card_for_process("Quality Check", child_lines if child_lines else line, True)
	job_card = job_card_data["top_job_card"]

	slab: Slab | None = None
	if job_card and job_card.slab:
		slab = frappe.get_doc("Slab", job_card.slab)  # pyright: ignore[reportAssignmentType]

	if not slab:
		# If there are no active job cards, get the earliest finished slab
		slabs: list[Slab] = get_slabs_for(line, next_stage="Quality Check")  # pyright: ignore[reportAssignmentType]
		slab = slabs[0] if slabs else None

	slab_size = None
	if slab:
		slab_size_name = slab.template.split("-")[-1]
		slab_size = frappe.get_doc("Slab Size", slab_size_name)

	return {"slab": slab, "job_card": job_card, "slab_size": slab_size}


def _make_material_transfer_stock_entry(slab_number: str, grade: str | None, job_card: str):
	work_order = frappe.get_value("Job Card", job_card, "work_order")
	target_warehouse: str = frappe.get_value("Work Order", work_order, "fg_warehouse")  # pyright: ignore[reportAssignmentType]

	company: str = frappe.get_value("Job Card", job_card, "company")  # pyright: ignore[reportAssignmentType]
	company_abbr: str = frappe.get_value("Company", company, "abbr")  # pyright: ignore[reportAssignmentType]

	production_item = frappe.get_value("Job Card", job_card, "production_item")
	item_uom = frappe.get_value("Item", production_item, "stock_uom")
	parts = []
	if slab_number:
		parts = slab_number.split("-")

	try:
		stock_entry: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore[reportAssignmentType]
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.company = company
		stock_entry.slab_grade = grade
		stock_entry.slab_batch_no = parts[0] if len(parts) > 0 else None
		stock_entry.slab_serial_no = parts[-1] if len(parts) > 1 else parts[0]
		stock_entry.from_warehouse = target_warehouse

		if grade and ("premium" in grade.lower() or "pre" in grade.lower()):
			stock_entry.to_warehouse = PREMIUM_WAREHOUSE + " - " + company_abbr
		elif grade and ("standard" in grade.lower() or "std" in grade.lower()):
			stock_entry.to_warehouse = STANDARD_WAREHOUSE + " - " + company_abbr
		else:
			stock_entry.to_warehouse = REJECTED_WAREHOUSE + " - " + company_abbr
		stock_entry.append(
			"items",
			{
				"item_code": production_item,
				"qty": 1,
				"uom": item_uom,
				"s_warehouse": target_warehouse,
				"t_warehouse": stock_entry.to_warehouse,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()
		return stock_entry

	except Exception:
		raise


@frappe.whitelist()
def get_repair_options():
	field = frappe.get_meta("Slab Quality Report").get_field("repair")
	if field and field.options:
		return [opt.strip() for opt in field.options.split("\n") if opt.strip()]
	return []


def finish_qc_process(slab_number: str, slab_grade: str | None, job_card: str, publish_slab_event=True):

	# 2. Finish the job card and checkout the slab.
	finish_process(job_card, "Quality Check", False, slab_number=slab_number, slab_grade=slab_grade, publish_slab_event=publish_slab_event)

	# 3. Move the slab to specific warehouse based on grade by making a new stock entry - Material Transfer.
	_make_material_transfer_stock_entry(slab_number, slab_grade, job_card)
