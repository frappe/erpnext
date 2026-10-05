# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import add_days, today

# test_records = frappe.get_test_records('Maintenance Visit')


class TestMaintenanceVisit(FrappeTestCase):
	def setUp(self):
		self.sales_person = frappe.get_doc("Sales Person", "_Test Sales Person")

	def make_warranty_claim(self):
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

	def test_sales_order_visit_cancel_not_blocked_by_later_visit(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order()
		earlier = self.make_visit(so, "Partially Completed", mntc_date=today())
		self.make_visit(so, "Partially Completed", mntc_date=add_days(today(), 1))

		earlier.cancel()

		self.assertEqual(frappe.db.get_value("Maintenance Visit", earlier.name, "docstatus"), 2)


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


def make_sales_person(name):
	sales_person = frappe.get_doc({"doctype": "Sales Person", "sales_person_name": name})
	sales_person.insert(ignore_if_duplicate=True)

	return sales_person
