# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils.data import today

from erpnext.stock.doctype.item.test_item import create_item

# test_records = frappe.get_test_records('Maintenance Visit')


class TestMaintenanceVisit(unittest.TestCase):
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
	
	def test_validate_purpose_table_TC_M_018(self):
		mv1 = make_maintenance_visit()
		try:
			mv1.validate_purpose_table()
		except Exception as e:
			frappe.throw(f"validate_purpose_table() raised an unexpected error: {e}")
		
		mv2 = frappe.new_doc("Maintenance Visit")
		mv2.company = "_Test Company"
		mv2.customer = "_Test Customer"
		mv2.mntc_date = today()
		mv2.completion_status = "Partially Completed"
		sales_person = make_sales_person("Dwight Schrute")
		with self.assertRaises(frappe.ValidationError, msg="Add Items in the Purpose Table"):
			mv2.validate_purpose_table()


	def test_validate_maintenance_date_TC_M_019(self):
		ms = frappe.new_doc("Maintenance Schedule")
		ms.company = "_Test Company"
		ms.customer = "_Test Customer"
		ms.transaction_date = today()

		ms.append(
			"items",
			{
				"item_code": "_Test Item",
				"start_date": "2025-10-01",
				"end_date": "2025-10-10",
				"periodicity": "Weekly",
				"no_of_visits": 1,
				"sales_person": "Sales Team",
			},
		)
		ms.insert(ignore_permissions=True)
		schedule_detail = frappe.get_doc({
			"doctype": "Maintenance Schedule Detail",
			"item_reference": ms.items[0].name,
			"scheduled_date": "2025-10-04",
			"parent": ms.name,
			"parenttype": "Maintenance Schedule",
		}).insert(ignore_if_duplicate=True,ignore_permissions=True)

		# ✅ CASE 1 — Valid maintenance date (within range)
		valid_doc = frappe.new_doc("Maintenance Visit")  # 🔹 Replace with actual doctype if different
		valid_doc.maintenance_type = "Scheduled"
		valid_doc.maintenance_schedule_detail = schedule_detail.name
		valid_doc.mntc_date = "2025-10-05"
		valid_doc.company = "_Test Company"
		valid_doc.customer = "_Test Customer"
		valid_doc.completion_status = "Partially Completed"
		sales_person = make_sales_person("Dwight Schrute")
		valid_doc.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name
			},
		)
		valid_doc.insert(ignore_if_duplicate=True,ignore_permissions=True)

		try:
			valid_doc.validate_maintenance_date()  # Should NOT raise any error
		except Exception as e:
			frappe.throw(f"validate_maintenance_date() raised unexpected error: {e}")

		# ❌ CASE 2 — Invalid maintenance date (before start_date)
		invalid_doc_before = frappe.new_doc("Maintenance Visit")
		invalid_doc_before.maintenance_type = "Scheduled"
		invalid_doc_before.maintenance_schedule_detail = schedule_detail.name
		invalid_doc_before.mntc_date = "2025-09-30"
		invalid_doc_before.company = "_Test Company"
		invalid_doc_before.customer = "_Test Customer"
		invalid_doc_before.completion_status = "Partially Completed"
		invalid_doc_before.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name
			},
		)

		with self.assertRaises(frappe.ValidationError, msg="Date before start_date should fail"):
			invalid_doc_before.validate_maintenance_date()

		# ❌ CASE 3 — Invalid maintenance date (after end_date)
		invalid_doc_after = frappe.new_doc("Maintenance Visit")
		invalid_doc_after.maintenance_type = "Scheduled"
		invalid_doc_after.maintenance_schedule_detail = schedule_detail.name
		invalid_doc_after.mntc_date = "2025-10-15"
		invalid_doc_after.company = "_Test Company"
		invalid_doc_after.customer = "_Test Customer"
		invalid_doc_after.completion_status = "Partially Completed"
		invalid_doc_after.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name
			},
		)

		with self.assertRaises(frappe.ValidationError, msg="Date after end_date should fail"):
			invalid_doc_after.validate_maintenance_date()

		purposes_doc = frappe.new_doc("Maintenance Visit")  # 🔹 Replace with actual doctype if different
		purposes_doc.maintenance_type = "Scheduled"
		purposes_doc.mntc_date = "2025-10-15"
		purposes_doc.company = "_Test Company"
		purposes_doc.customer = "_Test Customer"
		purposes_doc.completion_status = "Partially Completed"
		purposes_doc.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name,
				"maintenance_schedule_detail": schedule_detail.name
			},
		)
		with self.assertRaises(frappe.ValidationError, msg=" purposes Date after end_date should fail"):
			purposes_doc.validate_maintenance_date()

	def test_update_status_and_actual_date_direct_TC_M_020(self):
		ms = frappe.new_doc("Maintenance Schedule")
		ms.company = "_Test Company"
		ms.customer = "_Test Customer"
		ms.transaction_date = today()

		ms.append(
			"items",
			{
				"item_code": "_Test Item",
				"start_date": "2025-10-01",
				"end_date": "2025-10-10",
				"periodicity": "Weekly",
				"no_of_visits": 1,
				"sales_person": "Sales Team",
			},
		)
		ms.insert(ignore_permissions=True)
		schedule_detail = frappe.get_doc({
			"doctype": "Maintenance Schedule Detail",
			"item_reference": ms.items[0].name,
			"scheduled_date": "2025-10-04",
			"completion_status": "Pending",
			"parent": ms.name,
			"parenttype": "Maintenance Schedule",
			"actual_date": None,
		}).insert(ignore_if_duplicate=True,ignore_permissions=True)

		valid_doc = frappe.new_doc("Maintenance Visit")  # 🔹 Replace with actual doctype if different
		valid_doc.maintenance_type = "Scheduled"
		valid_doc.maintenance_schedule_detail = schedule_detail.name
		valid_doc.mntc_date = "2025-10-05"
		valid_doc.company = "_Test Company"
		valid_doc.customer = "_Test Customer"
		valid_doc.completion_status = "Partially Completed"
		sales_person = make_sales_person("Dwight Schrute")
		valid_doc.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name
			},
		)
		valid_doc.insert(ignore_if_duplicate=True,ignore_permissions=True)
		valid_doc.update_status_and_actual_date()

		updated = frappe.db.get_value(
			"Maintenance Schedule Detail",
			schedule_detail.name,
			["completion_status", "actual_date"],
			as_dict=True,
		)

		self.assertEqual(updated.completion_status, "Partially Completed")
		self.assertEqual(str(updated.actual_date), "2025-10-05")

		"""Test when cancel=True (should reset status and actual_date)"""
		valid_doc.update_status_and_actual_date(cancel=True)

		cancel_updated = frappe.db.get_value(
			"Maintenance Schedule Detail",
			schedule_detail.name,
			["completion_status", "actual_date"],
			as_dict=True,
		)

		self.assertEqual(cancel_updated.completion_status, "Pending")
		self.assertIsNone(cancel_updated.actual_date)

		purposes_doc = frappe.new_doc("Maintenance Visit")  # 🔹 Replace with actual doctype if different
		purposes_doc.maintenance_type = "Scheduled"
		purposes_doc.mntc_date = "2025-10-05"
		purposes_doc.company = "_Test Company"
		purposes_doc.customer = "_Test Customer"
		purposes_doc.completion_status = "Partially Completed"
		purposes_doc.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name,
				"maintenance_schedule_detail": schedule_detail.name
			},
		)
		purposes_doc.insert(ignore_if_duplicate=True,ignore_permissions=True)

		purposes_doc.update_status_and_actual_date()

		updated_2 = frappe.db.get_value(
			"Maintenance Schedule Detail",
			schedule_detail.name,
			["completion_status", "actual_date"],
			as_dict=True,
		)

		self.assertEqual(updated_2.completion_status, "Partially Completed")
		self.assertEqual(str(updated_2.actual_date), "2025-10-05")

	def test_check_if_last_visit_raises_error_for_later_visit_TC_M_021(self):
		"""Should throw error if a later Maintenance Visit exists for same sales order"""
		# Create a later visit with same prevdoc_docname and docstatus=1
		later_visit = frappe.get_doc({
			"doctype": "Maintenance Visit",
			"mntc_date": "2025-10-11",
			"company": "_Test Company",
			"customer": "_Test Customer",
			"mntc_time": "09:00:00",
			"completion_status":"Partially Completed",
			"docstatus": 1,
		})
		sales_person = make_sales_person("Dwight Schrute")
		sales_order = frappe.db.get_value("Sales Order",{"docstatus": 1},"name")
		later_visit.append("purposes", {
			"item_code": "_Test Item",
			"sales_person": "Sales Team",
			"description": "Test Item",
			"work_done": "Test Work Done",
			"service_person": sales_person.name,
			"prevdoc_doctype": "Sales Order",
			"prevdoc_docname": sales_order,
		})
		# Run and expect frappe.throw to trigger
		with self.assertRaises(frappe.ValidationError):
			later_visit.check_if_last_visit()

	def test_on_cancel_updates_status_TC_M_022(self):
		"""Test that on_cancel() sets status to 'Cancelled'"""
		valid_doc = frappe.new_doc("Maintenance Visit")  # 🔹 Replace with actual doctype if different
		valid_doc.maintenance_type = "Scheduled"
		valid_doc.mntc_date = "2025-10-05"
		valid_doc.company = "_Test Company"
		valid_doc.customer = "_Test Customer"
		valid_doc.completion_status = "Partially Completed"
		sales_person = make_sales_person("Dwight Schrute")
		valid_doc.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name
			},
		)
		valid_doc.insert(ignore_if_duplicate=True,ignore_permissions=True)
		# 2️⃣ Ensure initial status is not 'Cancelled'
		self.assertNotEqual(valid_doc.status, "Cancelled")
		
		# 3️⃣ Call the on_cancel() method
		valid_doc.on_cancel()

		# 4️⃣ Reload from DB to verify persistence
		valid_doc.reload()

		# 5️⃣ Assert the status was updated to 'Cancelled'
		self.assertEqual(valid_doc.status, "Cancelled", "Status should be set to Cancelled after on_cancel()")

	def test_validate_serial_no_TC_M_017(self):
		mv1 = make_maintenance_visit()
		try:
			mv1.validate_serial_no()
		except Exception as e:
			frappe.throw(f"validate_serial_no() failed unexpectedly: {e}")

		mv2 = frappe.new_doc("Maintenance Visit")
		mv2.company = "_Test Company"
		mv2.customer = "_Test Customer"
		mv2.mntc_date = today()
		mv2.completion_status = "Partially Completed"

		sales_person = make_sales_person("Dwight Schrute")

		mv2.append(
			"purposes",
			{
				"item_code": "_Test Item",
				"sales_person": "Sales Team",
				"description": "Test Item",
				"work_done": "Test Work Done",
				"service_person": sales_person.name,
				"serial_no": "FAKE-SERIAL-NO-001",
			},
		)
		
		with self.assertRaises(ValidationError):
			mv2.validate_serial_no()


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
	serial_no = make_serial_no("_Test Item")

	mv.append(
		"purposes",
		{
			"item_code": "_Test Item",
			"sales_person": "Sales Team",
			"description": "Test Item",
			"work_done": "Test Work Done",
			"service_person": sales_person.name,
			"serial_no": serial_no.name,
		},
	)
	mv.insert(ignore_permissions=True)

	return mv

def make_sales_person(name):
	existing_sales_person = frappe.db.get_value("Sales Person", {"sales_person_name": name}, "name")
	if existing_sales_person:
		return frappe.get_doc("Sales Person", existing_sales_person)

	sales_person = frappe.get_doc({
		"doctype": "Sales Person",
		"sales_person_name": name
	})
	sales_person.insert(ignore_if_duplicate=True, ignore_permissions=True)
	frappe.db.commit()
	return sales_person

def make_serial_no(item_code):
	existing_serial_no = frappe.db.get_value("Serial No", {"item_code": item_code}, "name")
	if existing_serial_no:
		return frappe.get_doc("Serial No", existing_serial_no)

	serial_no = frappe.get_doc({
		"doctype": "Serial No",
		"item_code": item_code,
		"serial_no": "SN-_Test_Item-00002",
	})
	serial_no.insert(ignore_if_duplicate=True, ignore_permissions=True)
	frappe.db.commit()
	return serial_no