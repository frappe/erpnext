# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import now
from frappe.model.document import Document
from frappe import _

class EmployeeCheckinLog(Document):
	pass


@frappe.whitelist()
def add_employee_checkin_log_based_on_biometric_id(biometric_id, timestamp, device_id=None, log_type=None):
	"""Finds the relevant Employee using the biometric_id and creates a Employee Checkin Log.

	:param biometric_id: The Biometric/RF tag ID as set up in Employee DocType.
	:param timestamp: The timestamp of the Log. Currently expected in the following format as string: '2019-05-08 10:48:08.000000'
	:param device_id(optional): Location / Device ID. A short string is expected.
	:param log_type(optional): Direction of the Check-in if available (IN/OUT).
	"""

	if not biometric_id or not timestamp:
		frappe.throw(_("'biometric_id' and 'timestamp' are required."))

	employee = frappe.db.get_values("Employee", {"biometric_id": biometric_id},["name","employee_name","biometric_id"],as_dict=True)
	if len(employee) != 0:
		employee = employee[0]
	else:
		frappe.throw(_("No Employee found for the given 'biometric_id'."))

	doc = frappe.new_doc("Employee Checkin Log")
	doc.employee = employee.name
	doc.employee_name = employee.employee_name
	doc.time = timestamp
	doc.device_id = device_id
	doc.log_type = log_type
	doc.save()

	return doc
