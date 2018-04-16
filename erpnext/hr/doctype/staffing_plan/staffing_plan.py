# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class StaffingPlan(Document):
	pass
#ToDo: Validate duplicate designations in Staffing Plan Detail

@frappe.whitelist()
def get_current_employee_count(designation):
	if not designation:
		return False
	employee_count = frappe.db.sql("""select count(*) from `tabEmployee` where designation = %s and status='Active'""", designation)[0][0]
	return employee_count

@frappe.whitelist()
def get_active_staffing_plan(doctype, txt, searchfield, start, page_len, filters):
	conditions = "spd.designation='{0}' and sp.docstatus=1 and \
	sp.company='{1}'".format(filters.get("designation"), filters.get("company"))

	if(filters.get("department")): #Department is an optional field
		conditions += " and sp.department='{0}'".format(filters.get("department"))

	return frappe.db.sql("""select spd.parent
		from `tabStaffing Plan Detail` spd join `tabStaffing Plan` sp on spd.parent=sp.name
		where {0}""".format(conditions))
