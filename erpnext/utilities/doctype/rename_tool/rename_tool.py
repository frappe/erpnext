# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import bulk_rename


class RenameTool(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		file_to_rename: DF.Attach | None
		select_doctype: DF.Literal[None]
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_doctypes():
	return frappe.db.sql_list(
		"""select name from tabDocType
		where allow_rename=1 and module!='Core' order by name"""
	)


@frappe.whitelist()
def upload(select_doctype=None, rows=None):
	from frappe.utils.csvutils import read_csv_content_from_attached_file

	if not select_doctype:
		select_doctype = frappe.form_dict.select_doctype

	if not frappe.has_permission(select_doctype, "write"):
		raise frappe.PermissionError

	rows = read_csv_content_from_attached_file(frappe.get_doc("Rename Tool", "Rename Tool"))

	# bulk rename allows only 500 rows at a time, so we created one job per 500 rows
	for i in range(0, len(rows), 500):
		frappe.enqueue(
			method=bulk_rename,
			queue="long",
			doctype=select_doctype,
			rows=rows[i : i + 500],
		)
