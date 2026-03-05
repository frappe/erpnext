# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType


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
	PartyType = DocType("Party Type")
	get_party_type_query = frappe.qb.from_(PartyType).select(PartyType.name).orderby(PartyType.name)

	condition_list = []

	if filters and filters.get("account"):
		account_type = frappe.db.get_value("Account", filters.get("account"), "account_type")
		if account_type:
			if account_type in ["Receivable", "Payable"]:
				# Include Employee regardless of its configured account_type, but still respect the text filter
				condition_list.append(
					(PartyType.account_type == account_type) | (PartyType.name == "Employee")
				)
			else:
				condition_list.append(PartyType.account_type == account_type)

	for condition in condition_list:
		get_party_type_query = get_party_type_query.where(condition)

	if frappe.local.lang == "en":
		get_party_type_query = get_party_type_query.where(getattr(PartyType, searchfield).like(f"%{txt}%"))
		get_party_type_query = get_party_type_query.limit(page_len)
		get_party_type_query = get_party_type_query.offset(start)

		result = get_party_type_query.run()
	else:
		result = get_party_type_query.run()
		test_str = txt.lower()
		result = [row for row in result if test_str in frappe._(row[0]).lower()]
		result = result[start : start + page_len]

	return result or []
