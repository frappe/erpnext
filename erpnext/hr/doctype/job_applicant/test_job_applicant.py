# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe

from erpnext.hr.doctype.designation.test_designation import create_designation


class TestJobApplicant(unittest.TestCase):
	pass

def create_job_applicant(**args):
	args = frappe._dict(args)

	filters = {
		"applicant_name": args.applicant_name or "_Test Applicant",
		"email_id": args.email_id or "test_applicant@example.com",
	}

	if frappe.db.exists("Job Applicant", filters):
		return frappe.get_doc("Job Applicant", filters)

	job_applicant = frappe.get_doc({
		"doctype": "Job Applicant",
		"status": args.status or "Open",
		"designation":  create_designation().name
	})

	job_applicant.update(filters)
	job_applicant.save()

	return job_applicant
