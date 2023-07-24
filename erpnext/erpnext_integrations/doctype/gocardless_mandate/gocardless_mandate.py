# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class GoCardlessMandate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		customer: DF.Link
		disabled: DF.Check
		gocardless_customer: DF.Data
		mandate: DF.Data
	# end: auto-generated types
	pass
