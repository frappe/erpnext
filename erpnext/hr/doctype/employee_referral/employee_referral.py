# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.document import Document

class EmployeeReferral(Document):
	def validate(self):
		self.check_email_id_is_unique()
		self.set_full_name()

	def check_email_id_is_unique(self):
		pass

	def set_full_name(self):
		self.full_name = self.first_name + " "+self.last_name

@frappe.whitelist()
def create_job_applicant(source_name, target_doc=None):
	emp_ref = frappe.get_doc("Employee Referral", source_name)


	#just for Api call if some set status apart from default Status
	status = emp_ref.status
	if emp_ref.status in ["Pending", "In process"]:
		status = "Open"

	job_applicant = frappe.new_doc("Job Applicant")
	job_applicant.employee_referral = emp_ref.name
	job_applicant.status = status
	job_applicant.applicant_name = emp_ref.full_name
	job_applicant.email_id = emp_ref.email
	job_applicant.phone_number = emp_ref.contact_no

	job_applicant.save()
	frappe.msgprint(_("Job Applicant created successfully. {0}").format(get_link_to_form("Job Applicant", job_applicant.name)))
	emp_ref.db_set('status', "In Process")

	return emp_ref

