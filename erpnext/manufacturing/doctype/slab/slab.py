# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Slab(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		current_stage: DF.Literal["Distribution", "Pressing", "Heating", "Cooling", "Trimming", "Calibration 1", "Calibration 2", "Polishing 1", "Polishing 2", "Quality", "Finished"]
		grade: DF.Data | None
		line: DF.Link
		quality_assessment: DF.Data | None
		template: DF.Link
	# end: auto-generated types
	pass
