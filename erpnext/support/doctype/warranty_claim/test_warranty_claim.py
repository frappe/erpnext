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

	def test_partial_visit_submitted_or_cancelled_after_completion_keeps_claim_closed(self):
		claim = self.make_warranty_claim()
		self.make_maintenance_visit_for_claim(claim, "Fully Completed")
		partial_visit = self.make_maintenance_visit_for_claim(claim, "Partially Completed")
		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Closed")

		partial_visit.cancel()
		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Closed")

	def test_warns_when_serial_no_is_not_delivered_to_the_claim_customer(self):
		serial_no = frappe.get_doc(
			{
				"doctype": "Serial No",
				"serial_no": frappe.generate_hash(length=10),
				"item_code": "_Test Serialized Item",
				"company": "_Test Company",
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Serial No", serial_no.name, "warehouse", "_Test Warehouse - _TC")

		claim = self.make_warranty_claim()
		claim.item_code = "_Test Serialized Item"
		claim.serial_no = serial_no.name
		self.assertIn("still in stock", self.get_warning_on_save(claim))

		frappe.db.set_value(
			"Serial No",
			serial_no.name,
			{"warehouse": None, "customer": "_Test Customer 1", "status": "Delivered"},
		)
		self.assertIsNone(self.get_warning_on_save(claim), "warning must not repeat on an unchanged save")

		claim.customer = "_Test Customer 2"
		self.assertIn("_Test Customer 1", self.get_warning_on_save(claim))

		claim.customer = "_Test Customer 1"
		self.assertIsNone(self.get_warning_on_save(claim))

	def get_warning_on_save(self, claim) -> str | None:
		frappe.clear_messages()
		claim.save()
		return next(
			(log.message for log in frappe.local.message_log if log.get("indicator") == "orange"), None
		)
