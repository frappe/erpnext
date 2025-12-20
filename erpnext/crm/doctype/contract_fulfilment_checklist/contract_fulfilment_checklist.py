# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class ContractFulfilmentChecklist(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		fulfilled: DF.Check
		notes: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		requirement: DF.Data | None
	# end: auto-generated types

	pass
