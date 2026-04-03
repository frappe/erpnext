from typing import cast

import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.operation.api import get_open_job_cards
from erpnext.manufacturing.doctype.production_line.production_line import get_all_child_lines
from erpnext.manufacturing.doctype.slab.api import get_slabs_for
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.page.operator_station.operator_station import (
	get_top_job_card_for_process,
	start_process,
)


@frappe.whitelist()
def get_queue_data(line, station_name: str):
	# Check if the station is standalone
	is_warehouse_standalone = frappe.db.get_value("Warehouse", {"mfg_process_type": station_name, "production_line": line }, "is_standalone")
	# If it is, set the limit to 50, else set it to 1.
	limit = 50 if is_warehouse_standalone else 1

	# 1. Get Incoming Slabs (Ready for the current station)
	incoming_slabs = get_slabs_for(line, station_name, limit=limit)

	# 2. Get the current slab queue (Active Job Cards)
	# Fetch WIP job cards for the current process.
	# We exclude "Material Transferred" as those are done but waiting for next move.
	if line and not isinstance(line, list):
		child_lines = get_all_child_lines(line)
		if child_lines:
			line = child_lines
	slabs_queue = get_open_job_cards(
		process=station_name,
		line=line,
		include_wip=True,
		include_material_transferred=False,  # Explicitly exclude
	)

	return {"incoming_slabs": incoming_slabs, "slabs_queue": slabs_queue}


@frappe.whitelist()
def start_queue_process(slab_number: str, line: str, station_name: str):
	slab = cast(Slab, frappe.get_doc("Slab", slab_number))
	#    1. Get the job card for the current station on the given line.
	child_lines = get_all_child_lines(line)
	job_card_result: dict[str, JobCard] = get_top_job_card_for_process(station_name, child_lines if child_lines else line, False)
	job_card = job_card_result.get("top_job_card")
	if not job_card:
		frappe.throw("No Job Card found")
	job_card_name = job_card.name if job_card else None
	# if not job_card:
	# 	frappe.throw("No Job Card found for the process.")

	# job_card = cast(JobCard, job_card)

	#    2. Start the job card.
	#    3. Move the slab to the current station.
	start_process(
		job_card_name, slab_name=slab.name or "", slab_template=slab.template, process_name=station_name
	)

	#    4. Return the job card number.
	return job_card_name
