# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class PartyType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_type: DF.Literal["Payable", "Receivable"]
		party_type: DF.Link
	# end: auto-generated types

	pass


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_party_type(doctype, txt, searchfield, start, page_len, filters):
	cond = ""
	if filters and filters.get("account"):
		account_type = frappe.db.get_value("Account", filters.get("account"), "account_type")
		cond = "and account_type = '%s'" % account_type

	return frappe.db.sql(
		f"""select name from `tabParty Type`
			where `{searchfield}` LIKE %(txt)s {cond}
			order by name limit %(page_len)s offset %(start)s""",
		{"txt": "%" + txt + "%", "start": start, "page_len": page_len},
	)
