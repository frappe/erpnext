# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.query_builder import Case


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_task(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	search_str = f"%{txt}%"
	prefix_str = f"{txt}%"

	Task = frappe.qb.DocType("Task")
	query = frappe.qb.get_query("Task", fields=["name", "subject"], ignore_permissions=False)

	return (
		query.where(Task[searchfield].like(search_str) | Task.subject.like(search_str))
		.orderby(Case().when(Task.subject.like(prefix_str), 0).else_(1))
		.orderby(Case().when(Task[searchfield].like(prefix_str), 0).else_(1))
		.orderby(Task[searchfield])
		.orderby(Task.subject)
		.limit(page_len)
		.offset(start)
		.run()
	)
