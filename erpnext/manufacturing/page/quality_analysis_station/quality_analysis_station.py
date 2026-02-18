import erpnext.manufacturing.doctype.job_card.job_card_dashboard
from erpnext.manufacturing.doctype.production_line.production_line import get_all_child_lines
import json

import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.operation.api import get_open_job_cards
from erpnext.manufacturing.doctype.slab.api import get_slabs_for
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_quality_report.slab_quality_report import SlabQualityReport
from erpnext.manufacturing.page.operator_station.operator_station import (
	finish_process,
	get_top_job_card_for_process,
	start_process,
)


@frappe.whitelist()
def start_qa_process(slab_number: str):
	slab: Slab = frappe.get_doc("Slab", slab_number)
	#    1. Get the job card for quality analysis on the given line.
	job_card_result = get_top_job_card_for_process("Quality Check", slab.line, True)
	job_card = job_card_result.get("top_job_card")
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

		# 1. Create the slab quality report.
		_create_slab_quality_report(slab_number, report, shift)
		# 2. Finish the job card and checkout the slab.
		finish_process(job_card, "Quality Check", False)

		frappe.db.commit()

		return {"slab": slab_number, "job_card": job_card}

	except Exception:
		frappe.db.rollback()
		raise


@frappe.whitelist()
def get_slab_or_jobcard_for_qa(line: str, job_card_number: str | None = None):
	job_card: JobCard | None = None
	if job_card_number:
		job_card = frappe.get_doc("Job Card", job_card_number)

	# Else, get the earliest open job card for the operation.
	# if not job_card:
	# 	if line and not isinstance(line, list):
	# 		child_lines = get_all_child_lines(line)
	# 		if child_lines:
	# 			line = child_lines

	# 	job_cards = get_open_job_cards("Quality Check", line, True)
	child_lines = get_all_child_lines(line)
	job_card_data = get_top_job_card_for_process("Quality Check", child_lines if child_lines else line, True)
	# wip_job_cards = [jc for jc in job_cards if jc.status == "Work In Progress"]
	# job_card = wip_job_cards[0] if wip_job_cards else job_cards[0] if job_cards else None
	job_card = job_card_data["top_job_card"]

	slab: Slab | None = None
	if job_card and job_card.slab:
		slab = frappe.get_doc("Slab", job_card.slab)

	if not slab:
		# If there are no active job cards, get the earliest finished slab
		slabs = get_slabs_for(line, next_stage="Quality Check")
		slab = slabs[0] if slabs else None

	slab_size = None
	if slab:
		slab_size_name = slab.template.split("-")[-1]
		slab_size = frappe.get_doc("Slab Size", slab_size_name)

	return {"slab": slab, "job_card": job_card, "slab_size": slab_size}


def _create_slab_quality_report(slab_name: str, report: str | dict, shift: str):
	if isinstance(report, str):
		report = json.loads(report)

	doc: SlabQualityReport = frappe.new_doc("Slab Quality Report")
	doc.update(report)
	doc.shift = shift

	doc.insert(ignore_permissions=True)
	doc.submit()

	slab: Slab = frappe.get_doc("Slab", slab_name)
	# if slab.status != "Quarantine" and slab.is_cur_stage_complete:
	#     raise Exception("Slab is not in quarantine or is not complete.")

	last_history_item = next((h for h in slab.slab_history if h.station == "Quality Check"), None)
	if not last_history_item:
		raise Exception("Slab is not in quality check.")

	last_history_item.quality_report_name = doc.name

	slab.grade = doc.grade
	slab.quality_assessment = doc.name
	slab.save(ignore_permissions=True)

	return doc
