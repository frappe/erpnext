# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.model.rename_doc import bulk_rename


class RenameTool(Document):
	pass

@frappe.whitelist()
def get_doctypes():
	return frappe.db.sql_list("""select name from tabDocType
		where allow_rename=1 and module!='Core' order by name""")

@frappe.whitelist()
def upload(select_doctype=None, rows=None):
	from frappe.utils.csvutils import read_csv_content_from_attached_file
	if not select_doctype:
		select_doctype = frappe.form_dict.select_doctype

	if not frappe.has_permission(select_doctype, "write"):
		raise frappe.PermissionError

	rows = read_csv_content_from_attached_file(frappe.get_doc("Rename Tool", "Rename Tool"))

	return bulk_rename(select_doctype, rows=rows)
