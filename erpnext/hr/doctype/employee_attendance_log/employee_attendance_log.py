# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now
from frappe.model.document import Document
from frappe import _

class EmployeeAttendanceLog(Document):
	pass


@frappe.whitelist()
def add_log_based_on_biometric_rf_id(biometric_rf_id, timestamp, device_id=None, log_type=None):
	"""Finds the relevant Employee using the biometric_rf_id and creates a Employee Attendance Log.

	:param biometric_rf_id: The Biometric/RF tag ID as set up in Employee DocType.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id(optional): Location / Device ID. A short string is expected.
	:param log_type(optional): Direction of the Punch if available (IN/OUT).
	"""

	if not biometric_rf_id or not timestamp:
		frappe.throw(_("'biometric_rf_id' and 'timestamp' are required."))

	employee = frappe.db.get_values("Employee", {"biometric_rf_id": biometric_rf_id},["name","employee_name","biometric_rf_id"],as_dict=True)
	if len(employee) != 0:
		employee = employee[0]
	else:
		frappe.throw(_("No Employee found for the given 'biometric_rf_id'."))

	doc = frappe.new_doc("Employee Attendance Log")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	doc.save()

	return doc
