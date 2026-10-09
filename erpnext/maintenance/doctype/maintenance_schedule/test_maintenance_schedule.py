# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import format_date
from frappe.utils.data import add_days, formatdate, getdate, today

from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	get_serial_no_query,
	get_serial_nos_from_schedule,
	make_maintenance_visit,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestMaintenanceSchedule(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Stock Entry")

	def test_events_should_be_created_and_deleted(self):
		ms = make_maintenance_schedule()
		ms.generate_schedule()
		ms.submit()

		all_events = get_events(ms)
		self.assertGreater(len(all_events), 0)

		ms.cancel()
		events_after_cancel = get_events(ms)
		self.assertEqual(len(events_after_cancel), 0)

	def test_make_schedule(self):
		ms = make_maintenance_schedule()
		ms.save()
		i = ms.items[0]
		expected_dates = []
		expected_end_date = add_days(i.start_date, i.no_of_visits * 7)
		self.assertEqual(i.end_date, expected_end_date)

		i.no_of_visits = 2
		i.end_date = None
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
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		ms = make_maintenance_schedule(item_code=item_code)
		ms.submit()

		s_item = ms.schedules[0]
		mv = make_maintenance_visit(source_name=ms.name, item_name=item_code, s_id=s_item.name)
		mvi = mv.purposes[0]
		serial_nos = get_serial_nos_from_schedule(mvi.item_name, ms.name)
		self.assertEqual(serial_nos, [])

		# With serial no. set in schedule -> returns serial nos.
		make_serial_item_with_serial(self, item_code)
		deliver_serial_nos(item_code, ["TEST001", "TEST002"])
		ms = make_maintenance_schedule(
			item_code=item_code, serial_no="TEST001, TEST002", start_date=add_days(today(), 1)
		)
		ms.submit()

		s_item = ms.schedules[0]
		mv = make_maintenance_visit(source_name=ms.name, item_name=item_code, s_id=s_item.name)
		mvi = mv.purposes[0]
		serial_nos = get_serial_nos_from_schedule(mvi.item_name, ms.name)
		self.assertEqual(
			serial_nos,
			[
				frappe.db.get_value("Serial No", {"item_code": item_code, "serial_no": number}, "name")
				for number in ("TEST001", "TEST002")
			],
		)

	def test_schedule_with_serials(self):
		# Checks whether serials are automatically updated when changing in items table.
		# Also checks if other fields trigger generate schdeule if changed in items table.
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
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
		ms.items[0].end_date = None
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

	def test_validate_sales_order_duplicate_throws(self):
		# validate_sales_order joins Maintenance Schedule + its item filtering the PARENT schedule's
		# docstatus=1; a second schedule against a Sales Order already used by a submitted schedule
		# must be rejected.
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order()
		first = make_maintenance_schedule(sales_order=so.name)
		self.assertEqual(first.items[0].sales_order, so.name)
		first.submit()

		self.assertRaises(frappe.ValidationError, make_maintenance_schedule, sales_order=so.name)

	def test_maintenance_roles_can_make_visits_from_schedule(self):
		ms = make_maintenance_schedule()
		ms.submit()

		for index, role in enumerate(("Maintenance User", "Maintenance Manager")):
			user = make_fenced_user(f"schedule-visit-{index}@example.com", [role])
			with as_user(user):
				visit = make_maintenance_visit(source_name=ms.name, s_id=ms.schedules[index].name)
				visit.completion_status = "Partially Completed"
				visit.purposes[0].work_done = "Serviced"
				visit.insert()
				visit.submit()

			self.assertEqual(visit.docstatus, 1)

	def test_serial_no_query_needs_schedule_read(self):
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		ms = make_maintenance_schedule(item_code=item_code, serial_no="TEST001")
		filters = {"item_code": item_code, "schedule": ms.name}
		sales_user = make_fenced_user("schedule-serial-sales@example.com", ["Sales User"])
		maintenance_user = make_fenced_user("schedule-serial-maintenance@example.com", ["Maintenance User"])

		with as_user(sales_user):
			self.assertRaises(
				frappe.PermissionError, get_serial_no_query, "Serial No", "", "name", 0, 20, filters
			)
		with as_user(maintenance_user):
			serial_nos = get_serial_no_query("Serial No", "", "name", 0, 20, filters)
		self.assertEqual([row[1] for row in serial_nos], ["TEST001"])

	def test_maintenance_manager_can_submit_schedule_with_serials(self):
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		deliver_serial_nos(item_code, ["TEST001"])
		ms = make_maintenance_schedule(
			item_code=item_code, serial_no="TEST001", start_date=add_days(today(), 1)
		)
		maintenance_manager = make_fenced_user("schedule-serial-manager@example.com", ["Maintenance Manager"])

		with as_user(maintenance_manager):
			ms.submit()

		serial_no = frappe.db.get_value("Serial No", {"item_code": item_code, "serial_no": "TEST001"})
		self.assertEqual(
			frappe.db.get_value("Serial No", serial_no, "amc_expiry_date"), getdate(ms.items[0].end_date)
		)

	def test_validate_schedule_date_skips_holiday(self):
		# validate_schedule_date_for_holiday_list reads the holiday list via the converted
		# get_all("Holiday", {"parent": <list>}, pluck="holiday_date") and shifts a schedule date
		# that lands on a holiday back by a day; a non-holiday date is returned unchanged.
		from frappe.utils import getdate

		from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list

		holiday = add_days(today(), 5)
		hl = make_holiday_list(
			"_Test MS Holidays " + frappe.generate_hash("", 6),
			from_date=today(),
			to_date=add_days(today(), 10),
			holiday_dates=[{"holiday_date": holiday, "description": "Test Holiday"}],
		)

		ms = make_maintenance_schedule()
		# a Sales Person with no linked employee routes to the company-default-holiday-list branch
		sp = frappe.get_doc(
			{"doctype": "Sales Person", "sales_person_name": "_Test MS SP " + frappe.generate_hash("", 5)}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Company", ms.company, "default_holiday_list", hl.name)

		# a date on the holiday is shifted back one day...
		shifted = ms.validate_schedule_date_for_holiday_list(getdate(holiday), sp.name, today())
		self.assertEqual(getdate(shifted), getdate(add_days(holiday, -1)))

		# ...a non-holiday date is returned unchanged
		non_holiday = add_days(today(), 7)
		unchanged = ms.validate_schedule_date_for_holiday_list(getdate(non_holiday), sp.name, today())
		self.assertEqual(getdate(unchanged), getdate(non_holiday))

	def test_cancelling_renewal_restores_earlier_amc_date(self):
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		serial = frappe.db.get_value(
			"Serial No", {"item_code": item_code, "status": "Active"}, ["name", "serial_no"], as_dict=True
		)
		deliver_serial_nos(item_code, [serial.serial_no])
		first = make_maintenance_schedule(
			item_code=item_code, serial_no=serial.serial_no, start_date=add_days(today(), 1)
		)
		first.submit()
		renewal = make_maintenance_schedule(
			item_code=item_code, serial_no=serial.serial_no, start_date=add_days(first.items[0].end_date, 1)
		)
		renewal.submit()

		renewal.cancel()

		self.assertEqual(
			frappe.db.get_value("Serial No", serial.name, "amc_expiry_date"), getdate(first.items[0].end_date)
		)

	def test_visit_from_schedule_skips_completed_rows(self):
		ms = make_maintenance_schedule()
		ms.submit()
		frappe.db.set_value(
			"Maintenance Schedule Detail", ms.schedules[0].name, "completion_status", "Fully Completed"
		)

		visit = make_maintenance_visit(source_name=ms.name)

		self.assertEqual(
			[purpose.maintenance_schedule_detail for purpose in visit.purposes],
			[row.name for row in ms.schedules[1:]],
		)

	def test_one_event_per_schedule_row_when_item_repeats(self):
		ms = make_maintenance_schedule()
		ms.append("items", ms.items[0].as_dict(no_default_fields=True))
		ms.save()
		ms.submit()

		self.assertEqual(len(get_events(ms)), len(ms.schedules))

	def test_events_are_visible_to_the_sales_person(self):
		ms = make_maintenance_schedule()
		ms.items[0].sales_person = "_Test Sales Person"
		ms.save()
		ms.submit()
		events = frappe.get_all(
			"Event Participants",
			filters={"reference_doctype": ms.doctype, "reference_docname": ms.name},
			pluck="parent",
		)

		with self.set_user("test@example.com"):
			visible = frappe.get_list("Event", filters={"name": ("in", events)}, pluck="name")

		self.assertEqual(len(visible), len(ms.schedules))

	def test_pending_data_id_skips_completed_row(self):
		ms = make_maintenance_schedule()
		ms.append("items", ms.items[0].as_dict(no_default_fields=True))
		ms.save()
		ms.submit()
		completed = ms.schedules[0]
		completed.db_set("completion_status", "Fully Completed")
		pending = next(row for row in ms.schedules[1:] if row.scheduled_date == completed.scheduled_date)

		s_id = ms.get_pending_data(
			data_type="id",
			item_name=completed.item_name,
			s_date=formatdate(completed.scheduled_date, "dd-mm-yyyy"),
		)

		self.assertEqual(s_id, pending.name)

	def test_visits_cannot_exceed_days_in_range(self):
		self.assertRaises(
			frappe.ValidationError,
			make_maintenance_schedule,
			periodicity="Random",
			end_date=add_days(today(), 4),
			no_of_visits=10,
		)

	def test_holiday_shift_does_not_move_before_start_date(self):
		from erpnext.setup.doctype.holiday_list.test_holiday_list import make_holiday_list

		hl = make_holiday_list(
			"_Test MS Start Holidays " + frappe.generate_hash("", 6),
			from_date=add_days(today(), -5),
			to_date=add_days(today(), 10),
			holiday_dates=[
				{"holiday_date": add_days(today(), offset), "description": "Test Holiday"}
				for offset in (-1, 0, 1)
			],
		)
		frappe.db.set_value("Company", "_Test Company", "default_holiday_list", hl.name)

		ms = make_maintenance_schedule(periodicity="Random", end_date=add_days(today(), 2), no_of_visits=2)

		self.assertEqual(
			[getdate(row.scheduled_date) for row in ms.schedules], [getdate(add_days(today(), 2))] * 2
		)

	def test_typed_end_date_must_fit_visits(self):
		self.assertRaisesRegex(
			frappe.ValidationError,
			"need an End Date",
			make_maintenance_schedule,
			end_date=add_days(today(), 364),
		)

		ms = make_maintenance_schedule(end_date=add_days(today(), 364), no_of_visits=52)
		self.assertEqual(getdate(ms.items[0].end_date), getdate(add_days(today(), 364)))

	def test_calendar_quarter_fits_one_quarterly_visit(self):
		ms = make_maintenance_schedule(
			start_date="2027-01-01", end_date="2027-03-31", periodicity="Quarterly", no_of_visits=1
		)
		self.assertEqual(getdate(ms.items[0].end_date), getdate("2027-03-31"))

	def test_serial_in_stock_is_refused(self):
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		number = frappe.db.get_value("Serial No", {"item_code": item_code, "status": "Active"}, "serial_no")
		ms = make_maintenance_schedule(item_code=item_code, serial_no=number)

		self.assertRaisesRegex(frappe.ValidationError, "still in stock", ms.submit)

	def test_serial_sold_to_another_customer_is_allowed_with_warning(self):
		item_code = "_Test Serial Item"
		make_serial_item_with_serial(self, item_code)
		number = frappe.db.get_value("Serial No", {"item_code": item_code, "status": "Active"}, "serial_no")
		deliver_serial_nos(item_code, [number], customer="_Test Customer 1")
		ms = make_maintenance_schedule(item_code=item_code, serial_no=number, start_date=add_days(today(), 1))
		frappe.clear_messages()

		ms.submit()

		self.assertEqual(ms.docstatus, 1)
		self.assertIn("was sold to Customer", str(frappe.get_message_log()))


def deliver_serial_nos(item_code, numbers, customer="_Test Customer"):
	from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

	serial_nos = [
		frappe.db.get_value("Serial No", {"item_code": item_code, "serial_no": number}) for number in numbers
	]
	return create_delivery_note(
		item_code=item_code, serial_no=serial_nos, qty=len(serial_nos), customer=customer
	)


def make_serial_item_with_serial(self, item_code):
	serial_item_doc = create_item(item_code, is_stock_item=1)
	if not serial_item_doc.has_serial_no or not serial_item_doc.serial_no_series:
		serial_item_doc.has_serial_no = 1
		serial_item_doc.serial_no_series = "TEST.###"
		serial_item_doc.save(ignore_permissions=True)
	active_serials = frappe.db.get_all("Serial No", {"status": "Active", "item_code": item_code})
	if len(active_serials) < 2:
		make_serialized_item(self, item_code=item_code)


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
			"start_date": args.get("start_date") or today(),
			"end_date": args.get("end_date"),
			"periodicity": args.get("periodicity") or "Weekly",
			"no_of_visits": args.get("no_of_visits") or 4,
			"serial_no": args.get("serial_no"),
			"sales_person": "Sales Team",
			"sales_order": args.get("sales_order"),
		},
	)
	ms.insert(ignore_permissions=True)

	return ms
