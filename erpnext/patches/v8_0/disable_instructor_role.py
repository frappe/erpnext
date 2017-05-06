# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	""" 
		disable the instructor role for companies with domain other than
		Education.
	"""

	domains = frappe.db.sql_list("select domain from tabCompany")
	if "Education" not in domains:
		role = frappe.get_doc("Role", "Instructor")
		role.disabled = 1
		role.save(ignore_permissions=True)