# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.permissions

def execute():
	for user in frappe.db.sql_list("select distinct parent from `tabUserRole` where role='Employee'"):
		# if employee record does not exists, remove employee role!
		if not frappe.db.get_value("Employee", {"user_id": user}):
			try:
				user = frappe.get_doc("User", user)
				for role in user.get("user_roles", {"role": "Employee"}):
					user.get("user_roles").remove(role)
				user.save()
			except frappe.DoesNotExistError:
				pass
