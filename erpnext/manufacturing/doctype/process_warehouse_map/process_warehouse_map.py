# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProcessWarehouseMap(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fg_warehouse: DF.Link
		process_name: DF.Link
		production_line: DF.Link
		source_warehouse: DF.Link
		wip_warehouse: DF.Link
	# end: auto-generated types
	pass
