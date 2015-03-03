# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

from frappe.model.document import Document

class RenameTool(Document):
	pass

@frappe.whitelist()
def get_doctypes():
	return frappe.db.sql_list("""select name from tabDocType
		where ifnull(allow_rename,0)=1 and module!='Core' order by name""")

@frappe.whitelist()
def upload(select_doctype=None, rows=None):
	from frappe.utils.csvutils import read_csv_content_from_attached_file
	from frappe.model.rename_doc import rename_doc

	if not select_doctype:
		select_doctype = frappe.form_dict.select_doctype

	if not frappe.has_permission(select_doctype, "write"):
		raise frappe.PermissionError

	if not rows:
		rows = read_csv_content_from_attached_file(frappe.get_doc("Rename Tool", "Rename Tool"))
	if not rows:
		frappe.throw(_("Please select a valid csv file with data"))

	max_rows = 500
	if len(rows) > max_rows:
		frappe.throw(_("Maximum {0} rows allowed").format(max_rows))

	rename_log = []
	for row in rows:
		# if row has some content
		if len(row) > 1 and row[0] and row[1]:
			try:
				if rename_doc(select_doctype, row[0], row[1]):
					rename_log.append(_("Successful: ") + row[0] + " -> " + row[1])
					frappe.db.commit()
				else:
					rename_log.append(_("Ignored: ") + row[0] + " -> " + row[1])
			except Exception, e:
				rename_log.append("<span style='color: RED'>" + \
					_("Failed: ") + row[0] + " -> " + row[1] + "</span>")
				rename_log.append("<span style='margin-left: 20px;'>" + repr(e) + "</span>")

	return rename_log
