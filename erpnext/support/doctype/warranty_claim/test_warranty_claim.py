# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import today

from erpnext.setup.doctype.employee.test_employee import make_employee

test_records = frappe.get_test_records("Warranty Claim")


class TestWarrantyClaim(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def make_warranty_claim(self):
		# Warranty Claim is not a submittable doctype; it stays at docstatus 0.
		claim = frappe.new_doc("Warranty Claim")
		claim.status = "Open"
		claim.complaint_date = today()
		claim.customer = "_Test Customer"
		claim.item_code = "_Test Item"
		claim.complaint = "Device stopped working under warranty"
		claim.company = "_Test Company"
		claim.insert(ignore_permissions=True)
		return claim

	def make_maintenance_visit_for_claim(self, claim, completion_status):
		visit = frappe.new_doc("Maintenance Visit")
		visit.company = "_Test Company"
		visit.customer = "_Test Customer"
		visit.mntc_date = today()
		visit.maintenance_type = "Unscheduled"
		visit.completion_status = completion_status
		visit.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"service_person": "_Test Sales Person",
				"work_done": "Replaced the faulty component",
				"description": "Warranty repair",
				"prevdoc_doctype": "Warranty Claim",
				"prevdoc_docname": claim.name,
			},
		)
		visit.insert(ignore_permissions=True)
		visit.submit()
		return visit

	def test_visit_records_the_user_of_the_service_person(self):
		user = "test_warranty_service_person@example.com"
		frappe.db.set_value(
			"Sales Person", "_Test Sales Person", "employee", make_employee(user, company="_Test Company")
		)
		claim = self.make_warranty_claim()
		self.make_maintenance_visit_for_claim(claim, "Partially Completed")

		claim.reload()
		self.assertEqual(claim.resolved_by, user)

		frappe.db.set_value("Sales Person", "_Test Sales Person", "employee", None)
		claim = self.make_warranty_claim()
		self.make_maintenance_visit_for_claim(claim, "Partially Completed")

		claim.reload()
		self.assertFalse(claim.resolved_by)
		claim.save()
