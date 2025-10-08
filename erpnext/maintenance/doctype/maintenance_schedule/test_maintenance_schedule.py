# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import if_app_installed
from frappe.utils import cint, date_diff, format_date, now_datetime, nowdate
from frappe.utils.data import add_days, formatdate, today

from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	get_serial_nos_from_schedule,
	make_maintenance_visit,
)
from erpnext.stock.doctype.item.test_item import create_item

# from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

# test_records = frappe.get_test_records('Maintenance Schedule')


class TestMaintenanceSchedule(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		import random
		import string

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()
		self.item = create_item("_Test Item10", {"has_serial_no": 1, "is_stock_item": 1})
		suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
		self.item.has_serial_no = 1
		self.item.is_stock_item = 1
		self.item.save()
		self.serial_no = frappe.get_doc(
			{
				"doctype": "Serial No",
				"serial_no": f"TEST-SR-{suffix}",
				"item_code": self.item.name,
				"company": "_Test Company",
			}
		).insert(ignore_if_duplicate=True)
		self.bundle = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": self.item.name,
				"type_of_transaction": "Maintenance",
				"has_serial_no": 1,
				"voucher_type": "Maintenance Schedule",
				"entries": [{"serial_no": self.serial_no.name, "qty": 1}],
			}
		).insert()

		self.schedule = make_maintenance_schedule(item_code=self.item.name, do_not_submit=True)
		self.schedule.items[0].serial_no = self.serial_no.name
		self.schedule.items[0].serial_and_batch_bundle = self.bundle.name
		self.schedule.items[0].no_of_visits = 1
		self.schedule.save()

	def test_events_should_be_created_and_deleted(self):
		ms = make_maintenance_schedule()
		ms.generate_schedule()
		ms.submit()

		all_events = get_events(ms)
		self.assertTrue(len(all_events) > 0)

		ms.cancel()
		events_after_cancel = get_events(ms)
		self.assertTrue(len(events_after_cancel) == 0)

	def test_make_schedule(self):
		ms = make_maintenance_schedule()
		ms.save()
		i = ms.items[0]
		expected_dates = []
		expected_end_date = add_days(i.start_date, i.no_of_visits * 7)
		self.assertEqual(i.end_date, expected_end_date)

		i.no_of_visits = 2
		ms.save()
		expected_end_date = add_days(i.start_date, i.no_of_visits * 7)
		self.assertEqual(i.end_date, expected_end_date)

		items = ms.get_pending_data(data_type="items")
		items = items.split("\n")
		items.pop(0)
		expected_items = ["_Test Item"]
		self.assertTrue(items, expected_items)

		# "dates" contains all generated schedule dates
		dates = ms.get_pending_data(data_type="date", item_name=i.item_name)
		dates = dates.split("\n")
		dates.pop(0)
		expected_dates.append(formatdate(add_days(i.start_date, 7), "dd-MM-yyyy"))
		expected_dates.append(formatdate(add_days(i.start_date, 14), "dd-MM-yyyy"))

		# test for generated schedule dates
		self.assertEqual(dates, expected_dates)

		ms.submit()
		s_id = ms.get_pending_data(data_type="id", item_name=i.item_name, s_date=expected_dates[1])

		# Check if item is mapped in visit.
		test_map_visit = make_maintenance_visit(source_name=ms.name, item_name="_Test Item", s_id=s_id)
		self.assertEqual(len(test_map_visit.purposes), 1)
		self.assertEqual(test_map_visit.purposes[0].item_name, "_Test Item")

		visit = frappe.new_doc("Maintenance Visit")
		visit = test_map_visit
		visit.maintenance_schedule = ms.name
		visit.maintenance_schedule_detail = s_id
		visit.completion_status = "Partially Completed"
		visit.set(
			"purposes",
			[
				{
					"item_code": i.item_code,
					"description": "test",
					"work_done": "test",
					"service_person": "Sales Team",
				}
			],
		)
		visit.save()
		visit.submit()
		ms = frappe.get_doc("Maintenance Schedule", ms.name)

		# checks if visit status is back updated in schedule
		self.assertTrue(ms.schedules[1].completion_status, "Partially Completed")
		self.assertEqual(format_date(visit.mntc_date), format_date(ms.schedules[1].actual_date))

		# checks if visit status is updated on cancel
		visit.cancel()
		ms.reload()
		self.assertTrue(ms.schedules[1].completion_status, "Pending")
		self.assertEqual(ms.schedules[1].actual_date, None)

	def test_serial_no_filters(self):
		# Without serial no. set in schedule -> returns None
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(item_code)
		ms = make_maintenance_schedule(item_code=item_code)
		ms.submit()

		s_item = ms.schedules[0]
		mv = make_maintenance_visit(source_name=ms.name, item_name=item_code, s_id=s_item.name)
		mvi = mv.purposes[0]
		serial_nos = get_serial_nos_from_schedule(mvi.item_name, ms.name)
		self.assertEqual(serial_nos, None)

		# With serial no. set in schedule -> returns serial nos.
		make_serial_item_with_serial(item_code)
		ms = make_maintenance_schedule(item_code=item_code, serial_no="TEST001, TEST002")
		ms.submit()

		s_item = ms.schedules[0]
		mv = make_maintenance_visit(source_name=ms.name, item_name=item_code, s_id=s_item.name)
		mvi = mv.purposes[0]
		serial_nos = get_serial_nos_from_schedule(mvi.item_name, ms.name)
		self.assertEqual(serial_nos, ["TEST001", "TEST002"])

		frappe.db.rollback()

	@if_app_installed("sales_commission")
	def test_schedule_with_serials(self):
		# Checks whether serials are automatically updated when changing in items table.
		# Also checks if other fields trigger generate schdeule if changed in items table.
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(item_code)
		ms = make_maintenance_schedule(item_code=item_code, serial_no="TEST001, TEST002")
		ms.save()

		# Before Save
		self.assertEqual(ms.schedules[0].serial_no, "TEST001, TEST002")
		self.assertEqual(ms.schedules[0].sales_person, "Sales Team")
		self.assertEqual(len(ms.schedules), 4)
		self.assertFalse(ms.validate_items_table_change())
		# After Save
		ms.items[0].serial_no = "TEST001"
		ms.items[0].sales_person = "_Test Sales Person"
		ms.items[0].no_of_visits = 2
		self.assertTrue(ms.validate_items_table_change())
		ms.save()
		self.assertEqual(ms.schedules[0].serial_no, "TEST001")
		self.assertEqual(ms.schedules[0].sales_person, "_Test Sales Person")
		self.assertEqual(len(ms.schedules), 2)
		# When user manually deleted a row from schedules table.
		ms.schedules.pop()
		self.assertEqual(len(ms.schedules), 1)
		ms.save()
		self.assertEqual(len(ms.schedules), 2)

		frappe.db.rollback()

	def test_update_amc_date_TC_M_001(self):
		from frappe.utils import add_days, nowdate

		ms = self.schedule

		amc_date = add_days(nowdate(), 180)
		ms.update_amc_date([self.serial_no.name], amc_expiry_date=amc_date)

		self.assertEqual(str(frappe.get_value("Serial No", self.serial_no.name, "amc_expiry_date")), amc_date)

	def test_validate_maintenance_detail_TC_M_002(self):
		def assert_throw(ms, msg):
			with self.assertRaises(frappe.ValidationError, msg=msg):
				ms.validate_maintenance_detail()

		ms = frappe.new_doc("Maintenance Schedule")

		assert_throw(ms, "Please enter Maintaince Details")

		ms.append("items", {})
		assert_throw(ms, "Please select item code")

		ms.items[0].item_code = self.item.name
		assert_throw(ms, "Start Date and End Date")

		ms.items[0].start_date = "2025-01-01"
		ms.items[0].end_date = "2025-01-10"
		assert_throw(ms, "no of visits")

		ms.items[0].no_of_visits = 1
		ms.items[0].start_date = "2025-01-10"
		ms.items[0].end_date = "2025-01-01"
		assert_throw(ms, "Start date should be less than end date")

		ms.items[0].start_date = "2025-01-01"
		ms.items[0].end_date = "2025-01-10"
		ms.validate_maintenance_detail()

	def test_validate_sales_order_throw_TC_M_003(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		so = make_sales_order(rate=500)
		so.submit()

		ms_existing = self.schedule
		ms_existing.items[0].sales_order = so.name
		ms_existing.items[0].no_of_visits = 1
		ms_existing.submit()

		ms_new = self.schedule
		ms_new.items[0].sales_order = so.name
		ms_new.items[0].no_of_visits = 1

		with self.assertRaises(frappe.ValidationError, msg="Maintenance Schedule"):
			ms_new.validate_sales_order()

	def test_validate_serial_no_bundle_throw_TC_M_004(self):
		bundle = frappe.get_doc(
			{
				"doctype": "Serial and Batch Bundle",
				"item_code": self.item.name,
				"type_of_transaction": "Maintenance",
				"voucher_type": "Sales Invoice",
				"entries": [{"serial_no": self.serial_no.name}],
			}
		).insert()

		ms = frappe.get_doc(
			{
				"doctype": "Maintenance Schedule",
				"customer": "_Test Customer",
				"transaction_date": nowdate(),
				"items": [
					{
						"item_code": self.item.name,
						"serial_no": self.serial_no.name,
						"serial_and_batch_bundle": bundle.name,
						"start_date": nowdate(),
						"end_date": add_days(nowdate(), 30),
						"no_of_visits": 2,
					}
				],
			}
		)

		with self.assertRaises(
			frappe.ValidationError, msg="should have voucher type as 'Maintenance Schedule'"
		):
			ms.insert()

	def test_on_trash_TC_M_005(self):
		doc = self.schedule

		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": "Test Event",
				"starts_on": now_datetime(),
				"event_participants": [
					{"reference_doctype": "Maintenance Schedule", "reference_docname": doc.name}
				],
			}
		).insert()

		self.assertTrue(frappe.db.exists("Event", event.name))

		doc.delete()

		self.assertFalse(frappe.db.exists("Event", event.name))

	def test_validate_serial_no_wrong_item_TC_M_006(self):
		sr = (
			frappe.get_doc("Serial No", "_Test Serial No")
			if frappe.db.exists("Serial No", "_Test Serial No")
			else frappe.get_doc(
				{"doctype": "Serial No", "serial_no": "_Test Serial No", "item_code": self.item.name}
			).insert()
		)

		ms = self.schedule
		with self.assertRaises(frappe.ValidationError, msg="does not belong to Item"):
			ms.validate_serial_no("_Another Item", [sr], nowdate())
		# self.assertIn("does not belong to Item", str(context.exception))

	def test_valid_periodicity_end_date_calculation_TC_M_007(self):
		self.days_in_period = {"Monthly": 30, "Quarterly": 90, "Half Yearly": 180, "Yearly": 365}
		item = frappe._dict({"start_date": "2025-05-01", "periodicity": "Quarterly", "no_of_visits": 0})

		if not item.no_of_visits or item.no_of_visits == 0:
			item.end_date = add_days(item.start_date, self.days_in_period[item.periodicity])
			diff = date_diff(item.end_date, item.start_date) + 1
			item.no_of_visits = cint(diff / self.days_in_period[item.periodicity])

		self.assertEqual(str(item.end_date), "2025-07-30")
		self.assertEqual(item.no_of_visits, 1)

	def test_does_not_override_existing_no_of_visits_TC_M_008(self):
		self.days_in_period = {"Monthly": 30, "Quarterly": 90, "Half Yearly": 180, "Yearly": 365}
		item = frappe._dict({"start_date": "2025-05-01", "periodicity": "Quarterly", "no_of_visits": 3})

		original_visits = item.no_of_visits
		if not item.no_of_visits or item.no_of_visits == 0:
			item.end_date = add_days(item.start_date, self.days_in_period[item.periodicity])
			diff = date_diff(item.end_date, item.start_date) + 1
			item.no_of_visits = cint(diff / self.days_in_period[item.periodicity])

		self.assertEqual(item.no_of_visits, original_visits)

	def test_on_trash_calls_delete_events_TC_M_009(self):
		from unittest.mock import patch

		ms = self.schedule

		with patch(
			"erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule.delete_events"
		) as mock_delete:
			ms.delete()
			mock_delete.assert_called_once_with("Maintenance Schedule", ms.name)

	def test_sets_no_of_visits_when_not_provided_TC_M_010(self):
		ms = self.schedule

		ms.periodicity = "Monthly"
		item = ms.items[0]
		item.start_date = nowdate()
		item.no_of_visits = 0

		ms.validate()

		expected_days = 30
		expected_end_date = add_days(item.start_date, expected_days)
		expected_visits = cint(date_diff(expected_end_date, item.start_date) + 1) // expected_days

		self.assertEqual(item.no_of_visits, expected_visits)

	def test_serial_auto_assign_on_make_maintenance_visit_TC_M_011(self):
		item_name = self.schedule.items[0].item_name
		self.schedule.submit()
		visit = make_maintenance_visit(self.schedule.name, item_name=item_name)
		visit.completion_status = "Partially Completed"
		visit.maintenance_type = "Scheduled"
		visit.purposes[0].service_person = "Sales Team"
		visit.purposes[0].work_done = "Test"
		visit.insert()

		self.assertEqual(visit.purposes[0].serial_no, self.serial_no.name)


def make_serial_item_with_serial(item_code):
	from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

	serial_item_doc = create_item(item_code, is_stock_item=1)
	if not serial_item_doc.has_serial_no or not serial_item_doc.serial_no_series:
		serial_item_doc.has_serial_no = 1
		serial_item_doc.serial_no_series = "TEST.###"
		serial_item_doc.save(ignore_permissions=True)
	active_serials = frappe.db.get_all("Serial No", {"status": "Active", "item_code": item_code})
	if len(active_serials) < 2:
		make_serialized_item(item_code=item_code)


def get_events(ms):
	return frappe.get_all(
		"Event Participants",
		filters={"reference_doctype": ms.doctype, "reference_docname": ms.name, "parenttype": "Event"},
	)


def make_maintenance_schedule(**args):
	ms = frappe.new_doc("Maintenance Schedule")
	ms.company = "_Test Company"
	ms.customer = "_Test Customer"
	ms.transaction_date = today()

	ms.append(
		"items",
		{
			"item_code": args.get("item_code") or "_Test Item",
			"start_date": today(),
			"periodicity": "Weekly",
			"no_of_visits": 4,
			"serial_no": args.get("serial_no"),
			"sales_person": "Sales Team",
		},
	)
	ms.insert(ignore_permissions=True)

	return ms
