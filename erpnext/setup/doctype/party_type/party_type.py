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
	cond = ""
	account_type = None

	if filters and filters.get("account"):
		account_type = frappe.db.get_value("Account", filters.get("account"), "account_type")
		if account_type:
			if account_type in ["Receivable", "Payable"]:
				# Include Employee regardless of its configured account_type, but still respect the text filter
				cond = "and (account_type = %(account_type)s or name = 'Employee')"
			else:
				cond = "and account_type = %(account_type)s"

	# Build parameters dictionary
	params = {"txt": "%" + txt + "%", "start": start, "page_len": page_len}
	if account_type:
		params["account_type"] = account_type

	result = frappe.db.sql(
		f"""select name from `tabParty Type`
        where `{searchfield}` LIKE %(txt)s {cond}
        order by name limit %(page_len)s offset %(start)s""",
		params,
	)

	if not result and txt:
		# No match found — txt may be a translated DocType name (non-English locale).
		# Party Type names are stored in English, so fall back to matching against
		# translated names.
		if account_type and account_type in ["Receivable", "Payable"]:
			all_types = frappe.db.sql(
				"select name from `tabParty Type` where account_type = %(account_type)s or name = 'Employee' order by name",
				{"account_type": account_type},
			)
		elif account_type:
			all_types = frappe.db.sql(
				"select name from `tabParty Type` where account_type = %(account_type)s order by name",
				{"account_type": account_type},
			)
		else:
			all_types = frappe.db.sql("select name from `tabParty Type` order by name")

		search_txt = txt.lower()
		result = tuple((name,) for (name,) in all_types if search_txt in frappe._(name).lower())
		result = result[int(start) : int(start) + int(page_len)]

	return result or []
