# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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
		current_stage: DF.Literal["Distribution", "Pressing", "Heating", "Cooling", "Trimming", "Calibration 1", "Calibration 2", "Polishing 1", "Polishing 2", "Quality", "Finished"]
		grade: DF.Data | None
		line: DF.Link
		quality_assessment: DF.Data | None
		serial_number: DF.Int
		shipping_date: DF.Date | None
		slab_history: DF.Table[SlabHistory]
		template: DF.Link
	# end: auto-generated types
	pass
