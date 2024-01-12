# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class EmployeeGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.employee_group_table.employee_group_table import EmployeeGroupTable

		employee_group_name: DF.Data
		employee_list: DF.Table[EmployeeGroupTable]
	# end: auto-generated types

	pass
