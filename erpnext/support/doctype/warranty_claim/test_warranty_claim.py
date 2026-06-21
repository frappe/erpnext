# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt

import frappe
from frappe.utils.data import today

from erpnext.support.doctype.warranty_claim.warranty_claim import make_maintenance_visit
from erpnext.tests.utils import ERPNextTestSuite


class TestWarrantyClaim(ERPNextTestSuite):
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

	def test_make_maintenance_visit_maps_new_visit_when_none_completed(self):
		# No "Fully Completed" visit yet -> converted query returns nothing,
		# so a fresh Maintenance Visit draft is mapped from the claim.
		claim = self.make_warranty_claim()

		target = make_maintenance_visit(claim.name)

		self.assertIsNotNone(target)
		self.assertEqual(target.doctype, "Maintenance Visit")
		self.assertTrue(target.is_new())
		# item_code present -> a purpose row is mapped and back-linked to the claim
		self.assertEqual(len(target.purposes), 1)
		row = target.purposes[0]
		self.assertEqual(row.item_code, "_Test Item")
		self.assertEqual(row.prevdoc_doctype, "Warranty Claim")
		self.assertEqual(row.prevdoc_docname, claim.name)

	def test_make_maintenance_visit_returns_none_when_fully_completed_exists(self):
		# A submitted, "Fully Completed" visit pointing at the claim must be
		# found by the converted join query -> no new visit is mapped.
		claim = self.make_warranty_claim()
		visit = self.make_maintenance_visit_for_claim(claim, "Fully Completed")

		# Sanity: the seeded visit really is the one the query should match.
		self.assertEqual(visit.docstatus, 1)
		self.assertEqual(visit.completion_status, "Fully Completed")
		self.assertEqual(visit.purposes[0].prevdoc_docname, claim.name)

		self.assertIsNone(make_maintenance_visit(claim.name))

	def test_make_maintenance_visit_ignores_partially_completed(self):
		# A "Partially Completed" visit must NOT satisfy the query, so a new
		# visit is still mapped (the completion_status filter is exercised).
		claim = self.make_warranty_claim()
		self.make_maintenance_visit_for_claim(claim, "Partially Completed")

		target = make_maintenance_visit(claim.name)

		self.assertIsNotNone(target)
		self.assertTrue(target.is_new())
		self.assertEqual(target.doctype, "Maintenance Visit")

	def test_on_cancel_blocked_by_active_maintenance_visit(self):
		# on_cancel's converted query joins Maintenance Visit Purpose -> Maintenance Visit and
		# filters the PARENT visit's docstatus != 2; a submitted (non-cancelled) visit referencing
		# the claim must block cancellation.
		claim = self.make_warranty_claim()
		self.make_maintenance_visit_for_claim(claim, "Partially Completed")

		self.assertRaises(frappe.ValidationError, claim.on_cancel)

	def test_on_cancel_allowed_when_no_active_visit(self):
		# No referencing visit -> the query returns nothing -> the claim is marked Cancelled.
		claim = self.make_warranty_claim()

		claim.on_cancel()

		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Cancelled")
