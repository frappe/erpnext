# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CalibrationMachine(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.manufacturing.doctype.machine_head.machine_head import MachineHead
		from frappe.types import DF

		code: DF.Data
		heads: DF.Table[MachineHead]
		line: DF.Link
		machine_name: DF.Data
	# end: auto-generated types
	pass
