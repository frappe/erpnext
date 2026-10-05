# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import bulk_rename
from frappe.utils.csvutils import read_csv_content
from frappe.utils.deprecations import deprecated


class RenameTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		file_to_rename: DF.Attach | None
		select_doctype: DF.Link | None
	# end: auto-generated types

	pass


@frappe.whitelist()
@deprecated
def get_doctypes():
	# The Rename Tool page is System-Manager-only, and its sibling upload() below already checks
	# before doing anything; this listed every renameable doctype on the site to any caller.
	frappe.has_permission("Rename Tool", throw=True)

	return frappe.get_all(
		"DocType", filters={"allow_rename": 1, "module": ["!=", "Core"]}, order_by="name", pluck="name"
	)


@frappe.whitelist()
def upload(select_doctype: str | None = None, file_to_rename: str | None = None):
	if not select_doctype:
		select_doctype = frappe.form_dict.select_doctype

	if not frappe.has_permission(select_doctype, "write"):
		raise frappe.PermissionError

	file = get_file_to_rename(file_to_rename)
	rows = read_csv_content(file.get_content())

	# bulk rename allows only 500 rows at a time, so we created one job per 500 rows
	for i in range(0, len(rows), 500):
		frappe.enqueue(
			method=bulk_rename,
			queue="long",
			doctype=select_doctype,
			rows=rows[i : i + 500],
		)

	file.delete()


def get_file_to_rename(file_url: str | None) -> Document:
	filters = {"attached_to_doctype": "Rename Tool", "attached_to_name": "Rename Tool"}
	if file_url:
		filters["file_url"] = file_url

	file_name = frappe.db.get_value("File", filters, "name", order_by="creation desc")
	if not file_name:
		frappe.throw(_("Please attach a CSV file to rename"))

	return frappe.get_doc("File", file_name)
