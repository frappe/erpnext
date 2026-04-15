# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

ALLOWED_STAGES = ["Distribution", "Pressing", "Re-Pressing", "Heating", "Cooling", "Curing", "Trimming", "Calibration", "Polishing", "Quality Check", "Packed", "Shipped", "Discarded"]

class Slab(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory

		amended_from: DF.Link | None
		batch_code: DF.Data | None
		batch_number: DF.Data
		child_line: DF.Link | None
		consignment_number: DF.Data | None
		container_number: DF.Data | None
		crate_number: DF.Data | None
		created_on: DF.Datetime | None
		current_job_card: DF.Data | None
		grade: DF.Link | None
		is_cur_stage_complete: DF.Check
		is_paused: DF.Check
		is_prematurely_checked_out: DF.Check
		is_repressed: DF.Check
		line: DF.Link
		number: DF.Int
		packing_list_number: DF.Data | None
		quality_assessment: DF.Link | None
		serial_number: DF.Data
		shipping_date: DF.Date | None
		slab_history: DF.Table[SlabHistory]
		status: DF.Literal["Distribution", "Pressing", "Re-Pressing", "Heating", "Cooling", "Curing", "Trimming", "Calibration", "Polishing", "Quality Check", "Packed", "Shipped", "Discarded"]
		stock_item: DF.Link | None
		template: DF.Link
	# end: auto-generated types


	@property
	def last_active_job_card(self):
		if self.current_job_card:
			return self.current_job_card

		# Get the last slab history item that has a job card associated
		for history in reversed(self.slab_history):
			if history.job_card_number:
				return history.job_card_number

		return None
