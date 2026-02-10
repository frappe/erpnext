# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

ALLOWED_STAGES = ["Distribution", "Pressing", "Re-pressing", "Heating", "Cooling", "Quarantine", "Trimming", "Calibration", "Polishing", "Quality Check", "Packed", "Shipped", "Discarded"]

class Slab(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
		from frappe.types import DF

		amended_from: DF.Link | None
		batch_number: DF.Data
		consignment_number: DF.Data | None
		created_on: DF.Datetime | None
		current_job_card: DF.Data | None
		grade: DF.Link | None
		is_cur_stage_complete: DF.Check
		is_prematurely_unquarantined: DF.Check
		is_repressed: DF.Check
		line: DF.Link
		number: DF.Int
		packing_list_number: DF.Data | None
		quality_assessment: DF.Link | None
		serial_number: DF.Data
		shipping_date: DF.Date | None
		slab_history: DF.Table[SlabHistory]
		status: DF.Literal["Distribution", "Pressing", "Re-pressing", "Heating", "Cooling", "Quarantine", "Trimming", "Calibration", "Polishing", "Quality Check", "Packed", "Shipped", "Discarded"]
		template: DF.Link
	# end: auto-generated types
	pass
