# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import today

from erpnext.stock.doctype.item.test_item import create_item

# test_records = frappe.get_test_records('Maintenance Visit')


class TestMaintenanceVisit(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, create_customer

		create_company()
		self.customer = create_customer("_Test Customer", currency="INR")
		self.item_code = create_item("_Test Item", is_stock_item=1)
		self.company = "_Test Company"
		self.sales_person = make_sales_person("_Test Sales Person")

	def tearDown(self):
		frappe.db.rollback()

	def test_update_customer_issue_sets_resolution_fields_TC_M_012(self):
		sales_person = self.sales_person
		wc = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"item_code": "_Test Item",
				"customer": "_Test Customer",
				"complaint": "Test",
				"status": "Open",
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv = frappe.get_doc(
			{
				"doctype": "Maintenance Visit",
				"mntc_date": frappe.utils.nowdate(),
				"company": "_Test Company",
				"customer": "_Test Customer",
				"completion_status": "Fully Completed",
				"purposes": [
					{
						"prevdoc_doctype": "Warranty Claim",
						"prevdoc_docname": wc.name,
						"work_done": "Test resolution work",
						"service_person": sales_person.name,
					}
				],
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv.update_customer_issue(flag=1)

		updated_wc = frappe.get_doc("Warranty Claim", wc.name)

		self.assertEqual(updated_wc.status, "Closed")
		self.assertEqual(updated_wc.resolution_details, "Test resolution work")
		self.assertEqual(str(updated_wc.resolution_date.date()), mv.mntc_date)

	def test_update_customer_issue_from_patial_maintenance_visit_TC_M_013(self):
		wc = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"customer": "_Test Customer",
				"item_code": "_Test Item",
				"complaint": "Test",
				"status": "Open",
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv = make_maintenance_visit()
		mv.purposes[0].prevdoc_docname = wc.name
		mv.completion_status = "Partially Completed"
		mv.purposes[0].prevdoc_doctype = "Warranty Claim"
		mv.update_customer_issue(flag=1)

		wc.reload()
		self.assertEqual(wc.status, "Work In Progress")

	def test_update_customer_issue_from_maintenance_visit_TC_M_014(self):
		wc = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"customer": "_Test Customer",
				"item_code": "_Test Item",
				"complaint": "Test",
				"status": "Open",
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv = make_maintenance_visit()
		mv.purposes[0].prevdoc_docname = wc.name
		mv.completion_status = "Fully Completed"
		mv.purposes[0].prevdoc_doctype = "Warranty Claim"
		mv.update_customer_issue(flag=1)

		wc.reload()
		self.assertEqual(wc.status, "Closed")
		mv1 = make_maintenance_visit()
		mv1.purposes[0].prevdoc_docname = wc.name
		mv1.completion_status = "Fully Completed"
		mv1.purposes[0].prevdoc_doctype = "Warranty Claim"
		mv1.update_customer_issue(flag=0)
		if "sales_commission" in frappe.get_installed_apps():
			self.assertNotEqual("service_person_field", "t2.service_person")
		else:
			self.assertEqual("service_person_field", "NULL")

	def test_future_maintenance_visit_prevents_cancel_TC_M_015(self):
		wc = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"customer": "_Test Customer",
				"item_code": "_Test Item",
				"complaint": "Tests",
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv1 = make_maintenance_visit()
		mv1.purposes[0].prevdoc_docname = wc.name
		mv1.purposes[0].prevdoc_doctype = "Warranty Claim"
		mv1.completion_status = "Fully Completed"
		mv1.update_customer_issue(flag=1)
		mv1.mntc_date = today()
		mv1.mntc_time = "10:00:00"
		mv1.submit()

		mv2 = make_maintenance_visit()
		mv2.purposes[0].prevdoc_docname = wc.name
		mv2.completion_status = "Fully Completed"
		mv2.purposes[0].prevdoc_doctype = "Warranty Claim"
		mv2.update_customer_issue(flag=1)
		mv2.mntc_date = today()
		mv2.mntc_time = "11:00:00"
		mv2.submit()

		with self.assertRaises(frappe.ValidationError, msg="Cancel Material Visits"):
			mv1.cancel()

	def test_update_customer_issue_flag_0_with_previous_partial_visit_TC_M_016(self):
		sales_person = self.sales_person

		wc = frappe.get_doc(
			{
				"doctype": "Warranty Claim",
				"customer": "_Test Customer",
				"item_code": "_Test Item",
				"complaint": "Test",
				"status": "Open",
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Maintenance Visit",
				"mntc_date": frappe.utils.nowdate(),
				"company": "_Test Company",
				"customer": "_Test Customer",
				"completion_status": "Partially Completed",
				"docstatus": 1,
				"purposes": [
					{
						"prevdoc_doctype": "Warranty Claim",
						"prevdoc_docname": wc.name,
						"work_done": "Partial fix done",
						"service_person": sales_person.name,
					}
				],
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv2 = frappe.get_doc(
			{
				"doctype": "Maintenance Visit",
				"mntc_date": frappe.utils.nowdate(),
				"company": "_Test Company",
				"customer": "_Test Customer",
				"completion_status": "Fully Completed",
				"purposes": [
					{
						"prevdoc_doctype": "Warranty Claim",
						"prevdoc_docname": wc.name,
						"work_done": "Partial fix done",
						"service_person": sales_person.name,
					}
				],
			}
		).insert(ignore_if_duplicate=True, ignore_permissions=True)

		mv2.update_customer_issue(flag=0)
		wc.reload()

		self.assertEqual(wc.status, "Work In Progress")
		self.assertEqual(wc.resolution_details, "Partial fix done")
		self.assertEqual(wc.resolved_by, "t2.service_person")


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
	if frappe.db.exists("Sales Person", {"sales_person_name": name}):
		return frappe.get_doc("Sales Person", {"sales_person_name": name})

	sales_person = frappe.get_doc({"doctype": "Sales Person", "sales_person_name": name})
	sales_person.insert(ignore_if_duplicate=True)

	return sales_person
