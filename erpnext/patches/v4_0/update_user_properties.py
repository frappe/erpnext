# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.permissions
import frappe.defaults

def execute():
	frappe.reload_doc("core", "doctype", "docfield")
	frappe.reload_doc("hr", "doctype", "employee")

	set_print_email_permissions()
	migrate_user_properties_to_user_permissions()

	frappe.clear_cache()

def migrate_user_properties_to_user_permissions():
	for d in frappe.db.sql("""select parent, defkey, defvalue from tabDefaultValue
		where parent not in ('__global', '__default')""", as_dict=True):
		df = frappe.db.sql("""select options from tabDocField
			where fieldname=%s and fieldtype='Link'""", d.defkey, as_dict=True)

		if df:
			frappe.db.sql("""update tabDefaultValue
				set defkey=%s, parenttype='User Permission'
				where defkey=%s and
				parent not in ('__global', '__default')""", (df[0].options, d.defkey))

def set_print_email_permissions():
	# reset Page perms
	from frappe.core.page.permission_manager.permission_manager import reset
	reset("Page")
	reset("Report")

	if "allow_print" not in frappe.db.get_table_columns("DocType"):
		return

	# patch to move print, email into DocPerm
	# NOTE: allow_print and allow_email are misnamed. They were used to hide print / hide email
	for doctype, hide_print, hide_email in frappe.db.sql("""select name, ifnull(allow_print, 0), ifnull(allow_email, 0)
		from `tabDocType` where ifnull(issingle, 0)=0 and ifnull(istable, 0)=0 and
		(ifnull(allow_print, 0)=0 or ifnull(allow_email, 0)=0)"""):

		if not hide_print:
			frappe.db.sql("""update `tabDocPerm` set `print`=1
				where permlevel=0 and `read`=1 and parent=%s""", doctype)

		if not hide_email:
			frappe.db.sql("""update `tabDocPerm` set `email`=1
				where permlevel=0 and `read`=1 and parent=%s""", doctype)
