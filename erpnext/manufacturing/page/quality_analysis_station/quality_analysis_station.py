from glob import iglob
from typing import Literal

import frappe
from frappe.utils.data import nowdate

from erpnext.manufacturing.doctype.job_card.job_card import JobCard, make_corrective_job_card
from erpnext.manufacturing.doctype.operation.api import (
	create_material_transfer_stock_entry,
	get_open_job_cards,
)
from erpnext.manufacturing.doctype.production_line.production_line import get_all_child_lines
from erpnext.manufacturing.doctype.slab.api import get_slabs_for
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_quality_report.api import create_slab_quality_report
from erpnext.manufacturing.doctype.slab_quality_report.slab_quality_report import SlabQualityReport
from erpnext.manufacturing.doctype.slab_repair_record.slab_repair_record import SlabRepairRecord
from erpnext.manufacturing.page.operator_station.operator_station import (
	finish_process,
	start_process,
)
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry


@frappe.whitelist()
def get_slab_or_jobcard_for_qa(
	line: str,
	job_card_number: str | None = None,
	slab_number: str | None = None,
	exclude_job_card: str | None = None,
):
	job_card: JobCard | None = None
	if job_card_number:
		job_card = frappe.get_doc("Job Card", job_card_number)  # pyright: ignore[reportAssignmentType]

	child_lines = get_all_child_lines(line)

	job_cards = get_open_job_cards(
		"Quality Check",
		child_lines if child_lines else line,
		include_wip=True,
		include_paused=True,
		exclude_job_cards=exclude_job_card or "",
	)

	if slab_number:
		job_card = next((job for job in job_cards if not job.slab or job.slab == slab_number), None)
	else:
		job_card = job_cards[0]

	slab: Slab | None = None
	if job_card and job_card.slab:
		slab = frappe.get_doc("Slab", job_card.slab)  # pyright: ignore[reportAssignmentType]

	if not slab and slab_number:
		slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]

	if not slab:
		# If there are no active job cards, get the earliest finished slab
		slabs: list[Slab] = get_slabs_for(line, next_stage="Quality Check")  # pyright: ignore[reportAssignmentType]
		slab = slabs[0] if slabs and slabs[0].status != "Recovery" else None
		if not slab:
			recovery_slabs = [slab for slab in slabs if slab.status == "Recovery"]
			for recovery_slab in recovery_slabs:
				slab_doc: Slab = frappe.get_doc("Slab", recovery_slab.name or "")  # pyright: ignore[reportAssignmentType]
				if slab_doc.is_cur_stage_complete and slab_doc.slab_history[-1].station == "Recovery":
					slab = slab_doc
					break

	slab_size = None
	if slab:
		slab_size_name = slab.template.split("-")[-1]
		slab_size = frappe.get_doc("Slab Size", slab_size_name)

	return {"slab": slab, "job_card": job_card, "slab_size": slab_size}


@frappe.whitelist()
def get_slab_queue(line: str, slab_to_exclude: str):
	slabs_for_qc = get_slabs_for(line, "Quality Check", limit=9999)
	# slabs = [slab for slab in slabs if not slab.status != 'Recovery' or (slab.is_cur_stage_complete and slab.slab_history[-1].station == 'Recovery')]
	slabs = []
	for slab in slabs_for_qc:
		if slab.name == slab_to_exclude:
			continue

		if slab.status != "Recovery":
			slabs.append(slab)
			continue

		slab_doc: Slab = frappe.get_doc("Slab", slab.name or "")  # pyright: ignore[reportAssignmentType]
		if slab_doc.is_cur_stage_complete and slab_doc.slab_history[-1].station == "Recovery":
			slabs.append(slab_doc)

	return slabs


@frappe.whitelist()
def get_slab_qc_report(qc_name: str):
	qc: SlabQualityReport | None = frappe.get_doc("Slab Quality Report", qc_name) if qc_name else None  # pyright: ignore[reportAssignmentType]
	if not qc:
		return None

	qc.repair_history.sort(key=lambda r: r.idx, reverse=True)
	return qc.to_json()


@frappe.whitelist()
def start_qa_process(line: str, job_card_number: str, slab_number: str):
	slab_and_job_card = get_slab_or_jobcard_for_qa(line, job_card_number, slab_number)
	slab: Slab = slab_and_job_card.get("slab")  # pyright: ignore[reportAssignmentType]
	#    1. Get the job card for quality analysis off the given line.
	job_card: JobCard | None = slab_and_job_card.get("job_card")  # pyright: ignore[reportAssignmentType]
	if not job_card:
		frappe.throw("No Job Card found")
	job_card_name = job_card.name if job_card else ""
	#    2. Start the job card.
	#    3. Move the slab to quality check.
	skip_validation = slab.status == "Recovery"
	start_process(
		job_card_name,
		slab_name=slab.name or "",
		slab_template=slab.template,
		process_name="Quality Check",
		skip_stage_validation=skip_validation,
	)

	#    4. Return the job card number.
	return job_card_name


@frappe.whitelist()
def submit_qa_report(report: str | dict, shift: str, job_card: str, slab_number: str):
	try:
		frappe.db.begin()

		if isinstance(report, str):
			report = frappe.parse_json(report)

		report_name: str | None = report.get("name")  # pyright: ignore[reportAttributeAccessIssue]
		if report_name:
			existing_report: SlabQualityReport = frappe.get_doc("Slab Quality Report", report_name)  # pyright: ignore[reportAssignmentType]
			slab_qc = existing_report
		else:
			slab_qc: SlabQualityReport = frappe.new_doc("Slab Quality Report")  # pyright: ignore[reportAssignmentType]

		slab_qc.update(report)
		slab_qc.shift = shift

		# 1. Create the slab quality report.
		create_slab_quality_report(slab_number, slab_qc)

		if slab_qc.repair != "None":
			# Make repair log
			_make_repair_logs(job_card, slab_qc)

		# Then,
		finish_qc_process(slab_number, job_card, slab_qc)

		frappe.db.commit()

		return {"slab": slab_number, "job_card": job_card}

	except Exception:
		frappe.db.rollback()
		raise


def _make_material_transfer_stock_entry(
	slab_number: str, grade: str | None, job_card: str, use_for_samples: int
):
	work_order = frappe.get_value("Job Card", job_card, "work_order")
	slab_fg_warehouse: str = frappe.get_value("Work Order", work_order, "fg_warehouse")  # pyright: ignore[reportAssignmentType]

	company: str = frappe.get_value("Job Card", job_card, "company")  # pyright: ignore[reportAssignmentType]
	company_abbr: str = frappe.get_value("Company", company, "abbr")  # pyright: ignore[reportAssignmentType]

	production_item: str = frappe.get_value("Job Card", job_card, "production_item")  # pyright: ignore[reportAssignmentType]
	item_uom = frappe.get_value("Item", production_item, "stock_uom")
	parts = []
	is_reject = False

	if slab_number:
		parts = slab_number.split("-")

	try:
		stock_entry: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore[reportAssignmentType]
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.company = company
		stock_entry.posting_date = nowdate()
		stock_entry.slab_grade = grade
		stock_entry.slab_batch_no = parts[0] if len(parts) > 0 else None
		stock_entry.slab_serial_no = parts[-1] if len(parts) > 1 else parts[0]
		source_item_name = production_item
		target_item_name = production_item
		source_warehouse = slab_fg_warehouse
		target_warehouse = f"Finished Goods - {company_abbr}"

		if grade and ("reject" in grade.lower() or "rej" in grade.lower()):
			is_reject = True
			target_warehouse = "Rejected Slabs" if not use_for_samples else "Samples"
			target_warehouse = f"{target_warehouse} - {company_abbr}"

		stock_entry.append(
			"items",
			{
				"item_code": source_item_name,
				"s_warehouse": source_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		if source_item_name == target_item_name:
			stock_entry.items[0].t_warehouse = target_warehouse
			stock_entry.items[0].is_finished_item = 1
		else:
			stock_entry.append(
				"items",
				{
					"item_code": target_item_name,
					"t_warehouse": target_warehouse,
					"qty": 1,
					"uom": item_uom,
					"slab_no": slab_number,
					"to_slab_no": slab_number,
					"is_finished_item": 1,
				},
			)

		stock_entry.insert(ignore_permissions=True)
		stock_entry.submit()

		return stock_entry, is_reject

	except Exception:
		raise


def _update_item_and_status_on_slab(
	item_code: str, slab_number: str, is_rejected: bool, use_for_samples: int
):
	slab: Slab = frappe.get_doc("Slab", slab_number)  # pyright: ignore[reportAssignmentType]
	slab.reload()
	slab.stock_item = item_code
	if is_rejected:
		slab.status = "Rejected"
		slab.is_sample = use_for_samples

	slab.save(ignore_permissions=True)


@frappe.whitelist()
def get_repair_options():
	return {
		"repair": _get_slab_qc_options("repair"),
		"recovery_type": _get_slab_qc_options("recovery_type"),
		"repolish_type": _get_slab_qc_options("repolish_type"),
		"recalibration_type": _get_slab_qc_options("recalibration_type"),
		"shade": _get_slab_qc_options("shade"),
		"colour": _get_slab_qc_options("colour"),
	}


def _get_slab_qc_options(fieldname):
	meta = frappe.get_meta("Slab Quality Report")
	field = meta.get_field(fieldname)
	if field and field.options:
		if field.fieldtype == "Select":
			return [opt.strip() for opt in field.options.split("\n") if opt.strip()]
		elif field.fieldtype == "Table MultiSelect":
			child_meta = frappe.get_meta(field.options)
			link_field = next((f for f in child_meta.fields if f.fieldtype == "Link"), None)
			if link_field:
				return [d.name for d in frappe.get_all(link_field.options)]
	return []


def finish_qc_process(
	slab_number: str, job_card: str, slab_qc_report: SlabQualityReport, publish_slab_event=True
):
	# 2. Finish the job card and checkout the slab.
	slab_grade = slab_qc_report.grade
	use_for_samples = slab_qc_report.use_for_samples
	repair_type = slab_qc_report.repair

	finish_process(
		job_card,
		"Quality Check",
		False,
		slab_number=slab_number,
		slab_grade=slab_grade,
		publish_slab_event=publish_slab_event,
	)

	if slab_grade:
		# 3. Move the slab to specific warehouse based on grade by making a new stock entry - Material Transfer.
		stock_entry, is_reject = _make_material_transfer_stock_entry(
			slab_number, slab_grade, job_card, use_for_samples
		)

		# 4. Update the name of the stock item on the slab.
		_update_item_and_status_on_slab(
			str(stock_entry.items[-1].item_code), slab_number, is_reject, use_for_samples
		)
	else:
		_make_repair_stock_entry(repair_type, slab_number, job_card)
		_make_repair_job_cards(repair_type, slab_number, job_card)

		# Fetch job card details needed for the material transfer
		jc_details: dict[str, str] = frappe.db.get_value(
			"Job Card", job_card, ["work_order", "company", "production_item"], as_dict=True
		)  # pyright: ignore[reportAssignmentType]
		company: str = jc_details.get("company")  # pyright: ignore[reportAssignmentType]
		work_order: str = jc_details.get("work_order")  # pyright: ignore[reportAssignmentType]
		fg_item: str = jc_details.get("production_item")  # pyright: ignore[reportAssignmentType]

		# Determine the corrective operation station to find the newly created open job card
		next_operation = (
			"Calibration"
			if repair_type == "Recalibration"
			else "Polishing"
			if repair_type == "Repolish"
			else "Quality Check"
		)
		open_job_card: str = frappe.db.get_value(
			"Job Card",
			{"slab": slab_number, "operation": next_operation, "status": "Open", "docstatus": 0},
			"name",
			order_by="creation desc",
		)  # pyright: ignore[reportAssignmentType]

		if open_job_card:
			next_wo_doc = frappe.get_doc("Work Order", work_order)
			s_warehouse: str = next_wo_doc.fg_warehouse  # pyright: ignore[reportAttributeAccessIssue]
			t_warehouse: str = next_wo_doc.wip_warehouse  # pyright: ignore[reportAttributeAccessIssue]
			stock_uom: str = frappe.db.get_value("Item", fg_item, "stock_uom")  # pyright: ignore[reportAssignmentType]
			job_card_item: str = frappe.db.get_value(
				"Job Card Item",
				{"parent": open_job_card, "item_code": fg_item, "parenttype": "Job Card"},
				"name",
			)  # pyright: ignore[reportAssignmentType]

			create_material_transfer_stock_entry(
				next_wo=work_order,
				open_job_card=open_job_card,
				company=company,
				fg_item=fg_item,
				transfer_qty=1.0,
				current_job_card=job_card,
				stock_uom=stock_uom,
				s_warehouse=s_warehouse,
				t_warehouse=t_warehouse,
				job_card_item=job_card_item,
			)


def _make_repair_stock_entry(
	repair_type: Literal["", "None", "Recovery", "Repolish", "Recalibration"], slab_number: str, job_card: str
):
	# Repack the item from FG warehouse on the work order to the quality check warehouse.
	jc_details: dict[str, str] = frappe.get_value(
		"Job Card", job_card, ["work_order", "company", "production_item"], as_dict=True
	)  # pyright: ignore[reportAssignmentType]
	company: str = jc_details.get("company")  # pyright: ignore[reportAssignmentType]
	work_order: str = jc_details.get("work_order")  # pyright: ignore[reportAssignmentType]

	if repair_type == "Recovery":
		_make_recovery_stock_entry(slab_number, job_card, work_order, company)
	if repair_type == "Repolish":
		_make_polish_stock_entry(slab_number, job_card, work_order, company)
	if repair_type == "Recalibration":
		_make_calibration_stock_entry(slab_number, job_card, work_order, company)


def _make_recovery_stock_entry(slab_number: str, job_card: str, work_order: str, company: str):
	production_line: str = frappe.get_value("Slab", slab_number, "line")  # pyright: ignore[reportAssignmentType]
	# The target warehouse is the quality check warehouse since recovery doesn't have a job card or work order flow defined.
	target_warehouse: str = frappe.get_value(
		"Warehouse",
		{"mfg_process_type": "Quality Check", "company": company, "production_line": production_line},
		"name",
	)  # pyright: ignore[reportAssignmentType]
	target_item_name: str = frappe.get_value("Work Order Item", {"parent": work_order}, "item_code")  # pyright: ignore[reportAssignmentType]
	_make_repack_stock_entry(slab_number, job_card, work_order, company, target_warehouse, target_item_name)


def _make_polish_stock_entry(slab_number: str, job_card: str, work_order: str, company: str):
	production_line: str = frappe.get_value("Slab", slab_number, "line")  # pyright: ignore[reportAssignmentType]
	target_warehouse: str = frappe.get_value(
		"Warehouse",
		{"mfg_process_type": "Polishing", "company": company, "production_line": production_line},
		"name",
	)  # pyright: ignore[reportAssignmentType]

	source_warehouse: str = frappe.get_value("Job Card", job_card, "wip_warehouse")  # pyright: ignore[reportAssignmentType]
	source_item_name: str = frappe.db.get_value("Job Card Item", {"parent": job_card}, "item_code")
	production_item: str = frappe.get_value("Job Card", job_card, "production_item")
	target_item_name: str = frappe.db.get_value(
		"Item", {"item_name": ("like", f"{production_item} - Calibrated%")}, "name"
	)

	item_uom = frappe.get_value("Item", source_item_name, "stock_uom")
	parts = []
	if slab_number:
		parts = slab_number.split("-")

	try:
		stock_entry: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore[reportAssignmentType]
		stock_entry.stock_entry_type = "Repack"
		stock_entry.company = company
		stock_entry.work_order = work_order
		stock_entry.posting_date = nowdate()
		stock_entry.slab_batch_no = parts[0] if len(parts) > 0 else None
		stock_entry.slab_serial_no = parts[-1] if len(parts) > 1 else parts[0]

		stock_entry.append(
			"items",
			{
				"item_code": source_item_name,
				"s_warehouse": source_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.append(
			"items",
			{
				"item_code": target_item_name,
				"t_warehouse": target_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.submit()
	except Exception as e:
		raise e


def _make_calibration_stock_entry(slab_number: str, job_card: str, work_order: str, company: str):
	production_line: str = frappe.get_value("Slab", slab_number, "line")  # pyright: ignore[reportAssignmentType]
	target_warehouse: str = frappe.get_value(
		"Warehouse",
		{"mfg_process_type": "Calibration", "company": company, "production_line": production_line},
		"name",
	)  # pyright: ignore[reportAssignmentType]

	source_warehouse: str = frappe.get_value("Job Card", job_card, "wip_warehouse")  # pyright: ignore[reportAssignmentType]
	source_item_name: str = frappe.db.get_value("Job Card Item", {"parent": job_card}, "item_code")
	production_item: str = frappe.get_value("Job Card", job_card, "production_item")
	target_item_name: str = frappe.db.get_value(
		"Item", {"item_name": ("like", f"{production_item} - Trimmed%")}, "name"
	)

	item_uom = frappe.get_value("Item", source_item_name, "stock_uom")
	parts = []
	if slab_number:
		parts = slab_number.split("-")

	try:
		stock_entry: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore[reportAssignmentType]
		stock_entry.stock_entry_type = "Repack"
		stock_entry.company = company
		stock_entry.work_order = work_order
		stock_entry.posting_date = nowdate()
		stock_entry.slab_batch_no = parts[0] if len(parts) > 0 else None
		stock_entry.slab_serial_no = parts[-1] if len(parts) > 1 else parts[0]

		stock_entry.append(
			"items",
			{
				"item_code": source_item_name,
				"s_warehouse": source_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.append(
			"items",
			{
				"item_code": target_item_name,
				"t_warehouse": target_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.submit()
	except Exception as e:
		raise e


def _make_repack_stock_entry(
	slab_number: str,
	job_card: str,
	work_order: str,
	company: str,
	target_warehouse: str,
	target_item_name: str,
):
	# Repack the item from FG warehouse on the work order to the quality check warehouse.
	slab_fg_warehouse: str = frappe.get_value("Work Order", work_order, "fg_warehouse")  # pyright: ignore[reportAssignmentType]

	production_item: str = frappe.get_value("Job Card", job_card, "production_item")  # pyright: ignore[reportAssignmentType]
	item_uom = frappe.get_value("Item", production_item, "stock_uom")
	parts = []

	if slab_number:
		parts = slab_number.split("-")
	try:
		stock_entry: StockEntry = frappe.new_doc("Stock Entry")  # pyright: ignore[reportAssignmentType]
		stock_entry.stock_entry_type = "Repack"
		stock_entry.company = company
		stock_entry.posting_date = nowdate()
		stock_entry.slab_batch_no = parts[0] if len(parts) > 0 else None
		stock_entry.slab_serial_no = parts[-1] if len(parts) > 1 else parts[0]
		source_item_name = production_item
		source_warehouse = slab_fg_warehouse

		stock_entry.append(
			"items",
			{
				"item_code": source_item_name,
				"s_warehouse": source_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.append(
			"items",
			{
				"item_code": target_item_name,
				"t_warehouse": target_warehouse,
				"qty": 1,
				"uom": item_uom,
				"slab_no": slab_number,
				"to_slab_no": slab_number,
			},
		)

		stock_entry.submit()
	except Exception as e:
		raise e


def _make_repair_job_cards(
	repair_type: Literal["", "None", "Recovery", "Repolish", "Recalibration"], slab_number: str, job_card: str
):
	# TODO: This needs to be implmented for repolish and recalibration.
	_make_corrective_job_card_for("Quality Check", slab_number)
	if repair_type in ["Repolish", "Recalibration"]:
		_make_corrective_job_card_for("Polishing", slab_number)
	if repair_type == "Recalibration":
		_make_corrective_job_card_for("Calibration", slab_number)


def _make_corrective_job_card_for(station: str, slab_number: str):
	# Get the slab history
	slab_history = frappe.get_all(
		"Slab History",
		filters={"parent": slab_number},
		fields=["job_card_number", "station"],
		order_by="in_time ASC",
	)

	# Get the first QC job card
	first_qc_job_card = next((item.job_card_number for item in slab_history if item.station == station), None)
	if first_qc_job_card:
		jc_operation: str = frappe.get_value("Job Card", first_qc_job_card, "operation")  # pyright: ignore[reportAssignmentType]
		new_jc = make_corrective_job_card(first_qc_job_card, for_operation=jc_operation)
		new_jc.operation = station
		new_jc.save(ignore_permissions=True)


def _make_repair_logs(job_card: str, slab_qc: SlabQualityReport):
	# Create new repair log and auto-assign all the appropriate fields
	repair_log: SlabRepairRecord = frappe.new_doc("Slab Repair Record")  # pyright: ignore[reportAssignmentType]
	repair_log.update(slab_qc.as_dict())
	repair_log.name = None
	repair_log.job_card = job_card
	repair_log.repair_date = frappe.utils.now_datetime()  # pyright: ignore[reportAttributeAccessIssue]
	repair_log.idx = len(slab_qc.repair_history) + 1

	slab_status = "Recovery"
	if slab_qc.repair == "Recovery":
		repair_log.repair_reason = ", ".join(
			[r.recovery_reason for r in slab_qc.recovery_type if r.recovery_reason]
		)

	elif slab_qc.repair == "Repolish":
		repair_log.repair_reason = ", ".join(
			[r.repolish_reason for r in slab_qc.repolish_type if r.repolish_reason]
		)
		slab_status = "Polishing"

	elif slab_qc.repair == "Recalibration":
		repair_log.repair_reason = ", ".join(
			[r.recalibration_reason for r in slab_qc.recalibration_type if r.recalibration_reason]
		)
		slab_status = "Calibration"

	# Get the list of colours in the qc's meta
	qc_colours = _get_slab_qc_options("colour")

	slab_qc.colour = next(
		(color for color in qc_colours if color not in [r.colour for r in slab_qc.observations]),
		qc_colours[0],
	)  # Set the next colour from the list as QC's colour.
	slab_qc.repair_history.append(repair_log)

	slab_qc.remarks = ""
	slab_qc.recovery_type = []
	slab_qc.repolish_type = []
	slab_qc.recalibration_type = []
	slab_qc.save()

	slab: Slab = frappe.get_doc("Slab", slab_qc.slab)  # pyright: ignore[reportAssignmentType]
	slab.reload()
	slab.status = slab_status
	slab.save()
