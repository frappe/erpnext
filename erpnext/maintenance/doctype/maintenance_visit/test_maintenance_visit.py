# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.data import add_days, getdate, today

from erpnext.tests.utils import ERPNextTestSuite


class TestMaintenanceVisit(ERPNextTestSuite):
	def setUp(self):
		self.sales_person = make_sales_person("_Test Maintenance Service Person")

	def make_warranty_claim(self):
		# Warranty Claim is not submittable; it provides a real target for the
		# purposes-row Dynamic Link (prevdoc_doctype/prevdoc_docname).
		claim = frappe.new_doc("Warranty Claim")
		claim.status = "Open"
		claim.complaint_date = today()
		claim.customer = "_Test Customer"
		claim.item_code = "_Test Item"
		claim.complaint = "Device stopped working under warranty"
		claim.company = "_Test Company"
		claim.insert(ignore_permissions=True)
		return claim

	def make_visit(self, claim, completion_status, mntc_date=None, mntc_time=None, submit=True):
		visit = frappe.new_doc("Maintenance Visit")
		visit.company = "_Test Company"
		visit.customer = "_Test Customer"
		visit.mntc_date = mntc_date or today()
		if mntc_time:
			visit.mntc_time = mntc_time
		visit.maintenance_type = "Unscheduled"
		visit.completion_status = completion_status
		visit.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"service_person": self.sales_person.name,
				"work_done": "Replaced the faulty component",
				"description": "Warranty repair",
				"prevdoc_doctype": "Warranty Claim",
				"prevdoc_docname": claim.name,
			},
		)
		visit.insert(ignore_permissions=True)
		if submit:
			visit.submit()
		return visit

	def test_cancel_blocked_when_later_visit_exists(self):
		# check_if_last_visit's converted join query (B): cancelling an EARLIER
		# submitted visit must be blocked while a LATER one (greater mntc_date)
		# referencing the same prevdoc_docname is still active.
		claim = self.make_warranty_claim()
		earlier = self.make_visit(claim, "Partially Completed", mntc_date=today())
		later = self.make_visit(claim, "Partially Completed", mntc_date=add_days(today(), 5))

		# Sanity: both are submitted and share the prevdoc_docname the query keys on.
		self.assertEqual(earlier.docstatus, 1)
		self.assertEqual(later.docstatus, 1)
		self.assertEqual(later.purposes[0].prevdoc_docname, claim.name)

		# The throw originates in check_if_last_visit's query (B): a later visit exists.
		self.assertRaisesRegex(frappe.ValidationError, later.name, earlier.cancel)

	def test_cancel_blocked_by_same_date_later_time(self):
		# Same converted query (B), time-tiebreak branch: equal mntc_date, but the
		# blocking visit has a strictly greater mntc_time.
		claim = self.make_warranty_claim()
		earlier = self.make_visit(claim, "Partially Completed", mntc_date=today(), mntc_time="09:00:00")
		later = self.make_visit(claim, "Partially Completed", mntc_date=today(), mntc_time="15:00:00")

		self.assertRaisesRegex(frappe.ValidationError, later.name, earlier.cancel)

	def test_cancel_allowed_for_latest_visit(self):
		# The latest visit has no later sibling -> query (B) returns nothing ->
		# cancellation proceeds and the visit is marked Cancelled.
		claim = self.make_warranty_claim()
		earlier = self.make_visit(claim, "Partially Completed", mntc_date=today())
		later = self.make_visit(claim, "Partially Completed", mntc_date=add_days(today(), 5))

		later.cancel()

		self.assertEqual(frappe.db.get_value("Maintenance Visit", later.name, "docstatus"), 2)
		self.assertEqual(frappe.db.get_value("Maintenance Visit", later.name, "status"), "Cancelled")
		# The earlier one is untouched and still submitted.
		self.assertEqual(frappe.db.get_value("Maintenance Visit", earlier.name, "docstatus"), 1)

	def test_cancel_reopens_claim_to_work_in_progress_from_prior_partial(self):
		# Drives the status-update query (A) inside update_customer_issue(flag=0).
		# A submitted "Partially Completed" visit (prior) exists for the claim; when
		# a LATER "Fully Completed" visit is cancelled, query (A) finds that prior
		# partial visit and the Warranty Claim is reopened to "Work In Progress"
		# carrying the prior visit's resolution data.
		claim = self.make_warranty_claim()
		prior = self.make_visit(claim, "Partially Completed", mntc_date=today())
		latest = self.make_visit(claim, "Fully Completed", mntc_date=add_days(today(), 3))

		# After submitting the "Fully Completed" visit the claim is Closed.
		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Closed")

		# Cancelling the latest visit: no later sibling blocks it, so cancel runs
		# update_customer_issue(0), which executes query (A) and reopens the claim.
		latest.cancel()

		claim.reload()
		self.assertEqual(claim.status, "Work In Progress")
		# Resolution data is back-filled from the prior partial visit found by query (A).
		self.assertEqual(claim.resolved_by, self.sales_person.name)
		self.assertEqual(claim.resolution_details, prior.purposes[0].work_done)
		self.assertEqual(getdate(claim.resolution_date), getdate(prior.mntc_date))

	def test_cancel_reopens_claim_to_open_when_no_prior_partial(self):
		# Inverse of query (A): a lone "Fully Completed" visit with no prior
		# "Partially Completed" sibling -> query (A) returns nothing -> the claim
		# is reset to "Open" with cleared resolution fields on cancel.
		claim = self.make_warranty_claim()
		visit = self.make_visit(claim, "Fully Completed", mntc_date=today())
		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Closed")

		visit.cancel()

		claim.reload()
		self.assertEqual(claim.status, "Open")
		self.assertIsNone(claim.resolved_by)
		self.assertIsNone(claim.resolution_details)
		self.assertIsNone(claim.resolution_date)


def make_sales_person(name):
	sales_person = frappe.get_doc({"doctype": "Sales Person", "sales_person_name": name})
	sales_person.insert(ignore_if_duplicate=True)
	if not sales_person.name:
		sales_person = frappe.get_doc("Sales Person", {"sales_person_name": name})
	return sales_person


def make_maintenance_visit():
	mv = frappe.new_doc("Maintenance Visit")
	mv.company = "_Test Company"
	mv.customer = "_Test Customer"
	mv.mntc_date = today()
	mv.completion_status = "Partially Completed"

	sales_person = make_sales_person("Dwight Schrute")

	mv.append(
		"purposes",
		{
			"item_code": "_Test Item",
			"sales_person": "Sales Team",
			"description": "Test Item",
			"work_done": "Test Work Done",
			"service_person": sales_person.name,
		},
	)
	mv.insert(ignore_permissions=True)

	return mv
