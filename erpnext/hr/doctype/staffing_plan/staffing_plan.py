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
