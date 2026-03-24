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
def get_party_type(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	account_type = None

	if filters and filters.get("account"):
		account_type = frappe.db.get_value("Account", filters.get("account"), "account_type")
	query_filters = {searchfield: ["like", f"%{txt}%"]}
	or_filters = None

	if account_type:
		if account_type in ["Receivable", "Payable"]:
			# Include Employee regardless of its configured account_type, but still respect the text filter.
			or_filters = [{"account_type": account_type}, {"name": "Employee"}]
		else:
			query_filters["account_type"] = account_type

	result = frappe.get_list(
		"Party Type",
		filters=query_filters,
		or_filters=or_filters,
		fields=["name"],
		order_by="name",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)

	return result or []
