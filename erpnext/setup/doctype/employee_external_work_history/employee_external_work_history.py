# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class EmployeeExternalWorkHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		company_name: DF.Data | None
		contact: DF.Data | None
		designation: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		salary: DF.Currency
		total_experience: DF.Data | None
	# end: auto-generated types

	pass
