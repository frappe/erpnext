# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils.data import add_days, getdate, today

from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	make_maintenance_visit as make_visit_from_schedule,
)
from erpnext.maintenance.doctype.maintenance_schedule.test_maintenance_schedule import (
	deliver_serial_nos,
	make_maintenance_schedule,
	make_serial_item_with_serial,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestMaintenanceVisit(ERPNextTestSuite):
	def setUp(self):
		self.sales_person = frappe.get_doc("Sales Person", "_Test Sales Person")

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

	def make_visit(self, reference, completion_status, mntc_date=None, mntc_time=None, submit=True):
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
				"prevdoc_doctype": reference.doctype,
				"prevdoc_docname": reference.name,
			},
		)
		visit.insert(ignore_permissions=True)
		if submit:
			visit.submit()
		return visit

	def make_schedule_visit(
		self, schedule, detail, completion_status="Fully Completed", submit=True, **fields
	):
		visit = make_visit_from_schedule(schedule.name, s_id=detail)
		visit.completion_status = completion_status
		visit.mntc_date = today()
		visit.update(fields)
		for purpose in visit.purposes:
			purpose.service_person = self.sales_person.name
			purpose.work_done = "Serviced"
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

	def test_sales_order_visit_cancel_not_blocked_by_later_visit(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order()
		earlier = self.make_visit(so, "Partially Completed", mntc_date=today())
		self.make_visit(so, "Partially Completed", mntc_date=add_days(today(), 1))

		earlier.cancel()

		self.assertEqual(frappe.db.get_value("Maintenance Visit", earlier.name, "docstatus"), 2)

	def test_unscheduled_visit_for_schedule_row_checks_contract_dates(self):
		schedule = make_maintenance_schedule()
		schedule.submit()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Date must be between",
			self.make_schedule_visit,
			schedule,
			schedule.schedules[0].name,
			maintenance_type="Unscheduled",
			mntc_date=add_days(schedule.items[0].end_date, 30),
		)

	def test_visit_customer_must_match_schedule(self):
		schedule = make_maintenance_schedule()
		schedule.submit()

		self.assertRaises(
			frappe.ValidationError,
			self.make_schedule_visit,
			schedule,
			schedule.schedules[0].name,
			customer="_Test Customer 1",
		)

	def test_visit_rows_must_belong_to_its_submitted_schedule(self):
		schedule = make_maintenance_schedule()
		schedule.submit()
		other = make_maintenance_schedule()
		other.submit()

		self.assertRaises(
			frappe.ValidationError,
			self.make_schedule_visit,
			other,
			other.schedules[0].name,
			maintenance_schedule=schedule.name,
		)

		visit = self.make_schedule_visit(schedule, schedule.schedules[0].name, submit=False)
		schedule.cancel()
		self.assertRaises(frappe.ValidationError, visit.submit)

	def test_schedule_row_keeps_status_of_its_completing_visit(self):
		schedule = make_maintenance_schedule()
		schedule.submit()
		row = schedule.schedules[0].name
		self.make_schedule_visit(schedule, row)
		later = self.make_schedule_visit(schedule, row, "Partially Completed", mntc_date=add_days(today(), 1))
		self.assertEqual(
			frappe.db.get_value("Maintenance Schedule Detail", row, "completion_status"), "Fully Completed"
		)

		later.cancel()

		self.assertEqual(
			frappe.db.get_value("Maintenance Schedule Detail", row, ["completion_status", "actual_date"]),
			("Fully Completed", getdate(today())),
		)

	def test_cancelling_partial_visit_keeps_claim_closed_by_full_visit(self):
		claim = self.make_warranty_claim()
		partial = self.make_visit(claim, "Partially Completed")
		self.make_visit(claim, "Fully Completed")

		partial.cancel()

		self.assertEqual(frappe.db.get_value("Warranty Claim", claim.name, "status"), "Closed")

	def test_visit_serial_checked_against_stock_and_customer(self):
		self.load_test_records("Stock Entry")
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		in_stock, sold = frappe.get_all(
			"Serial No", filters={"item_code": item_code, "status": "Active"}, pluck="name", limit=2
		)
		visit = make_maintenance_visit()
		visit.purposes[0].item_code = item_code
		visit.purposes[0].serial_no = in_stock
		self.assertRaisesRegex(frappe.ValidationError, "still in stock", visit.save)

		deliver_serial_nos(
			item_code, [frappe.db.get_value("Serial No", sold, "serial_no")], "_Test Customer 1"
		)
		visit.reload()
		visit.purposes[0].item_code = item_code
		visit.purposes[0].serial_no = sold
		frappe.clear_messages()
		visit.save()
		self.assertIn("was sold to Customer", str(frappe.get_message_log()))

	def test_visit_allows_returned_serial_of_the_same_customer(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		self.load_test_records("Stock Entry")
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		serial = frappe.db.get_value(
			"Serial No", {"item_code": item_code, "status": "Active"}, ["name", "serial_no"], as_dict=True
		)
		delivery = deliver_serial_nos(item_code, [serial.serial_no])
		make_sales_return(delivery.name).submit()
		self.assertTrue(frappe.db.get_value("Serial No", serial.name, "warehouse"))

		visit = make_maintenance_visit()
		visit.purposes[0].item_code = item_code
		visit.purposes[0].serial_no = serial.name
		visit.save()

		self.assertEqual(visit.purposes[0].serial_no, serial.name)


def make_maintenance_visit():
	mv = frappe.new_doc("Maintenance Visit")
	mv.company = "_Test Company"
	mv.customer = "_Test Customer"
	mv.mntc_date = today()
	mv.completion_status = "Partially Completed"

	mv.append(
		"purposes",
		{
			"item_code": "_Test Item",
			"sales_person": "Sales Team",
			"description": "Test Item",
			"work_done": "Test Work Done",
			"service_person": "_Test Sales Person",
		},
	)
	mv.insert(ignore_permissions=True)

	return mv
