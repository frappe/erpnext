# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff

class Mine(Document):
	# def validate(self):
	# 	self.validate_date()

	def validate_date(self):
		if not self.lease_start_date and not self.lease_end_date:
			if self.lease_start_date > self.lease_end_date:
				frappe.throw("Lease Start Date cannot be greater than Lease End Date")

@frappe.whitelist()
def lease_duration(lease_start_date, lease_end_date):
	if lease_start_date and lease_end_date:
		lease_duration = date_diff(lease_end_date, lease_start_date)
		return lease_duration

@frappe.whitelist()
def ec_duration(ec_issue_date, ec_expiry_date):
	if ec_issue_date and ec_expiry_date:
		duration = date_diff(ec_expiry_date, ec_issue_date)
		return duration