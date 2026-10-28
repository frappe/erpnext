# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import frappe
<<<<<<< HEAD
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
=======
from frappe import _
from frappe.utils import get_datetime
>>>>>>> a6d3092 (test: operation planned start for a multi-day scheduled job card)

from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry
from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.routing.test_routing import create_routing, setup_bom
from erpnext.manufacturing.doctype.workstation.workstation import (
	NotInWorkingHoursError,
	OverlapError,
	WorkstationHolidayError,
	check_if_within_operating_hours,
	get_raw_materials,
)

test_dependencies = ["Warehouse", "Item"]
test_records = frappe.get_test_records("Workstation")
make_test_records("Workstation")


class TestWorkstation(FrappeTestCase):
	def make_workstation(self, name, *timings):
		doc = frappe.new_doc("Workstation", workstation_name=name)
		for start_time, end_time in timings:
			doc.append("working_hours", {"start_time": start_time, "end_time": end_time})
		return doc

	def test_back_to_back_working_hours_do_not_overlap(self):
		doc = self.make_workstation(
			"_Test Back To Back Shifts", ("08:00:00", "16:00:00"), ("16:00:00", "23:59:59")
		)
		doc.insert()

		# also holds when the touching row is added to an already saved workstation
		doc.append("working_hours", {"start_time": "05:00:00", "end_time": "08:00:00"})
		doc.save()
		self.assertEqual(len(doc.working_hours), 3)

	def test_overlapping_working_hours_raise_error(self):
		for timing in (
			("15:00:00", "20:00:00"),  # partial overlap at the end
			("06:00:00", "09:00:00"),  # partial overlap at the start
			("10:00:00", "12:00:00"),  # enclosed
			("07:00:00", "17:00:00"),  # enclosing
			("08:00:00", "16:00:00"),  # identical
		):
			with self.subTest(timing=timing):
				doc = self.make_workstation("_Test Overlapping Shifts", ("08:00:00", "16:00:00"))
				doc.insert()
				doc.append("working_hours", {"start_time": timing[0], "end_time": timing[1]})
				self.assertRaises(OverlapError, doc.save)
				doc.delete()

	def test_get_raw_materials_without_items(self):
		job_card = frappe.get_doc(
			{
				"doctype": "Job Card",
				"company": "_Test Company",
				"wip_warehouse": "_Test Warehouse 1 - _TC",
			}
		).insert(ignore_mandatory=True)

		self.assertEqual(get_raw_materials([job_card.name]), {})
		with self.assertRaisesRegex(frappe.ValidationError, "This Job Card has no raw materials to transfer"):
			make_stock_entry(job_card.name)

		job_card.reload()
		self.assertFalse(job_card.items)
		self.assertFalse(frappe.db.exists("Stock Entry", {"job_card": job_card.name}))

	def test_get_raw_materials_with_items(self):
		job_card = frappe.get_doc(
			{
				"doctype": "Job Card",
				"company": "_Test Company",
				"wip_warehouse": "_Test Warehouse 1 - _TC",
				"items": [
					{
						"item_code": "_Test Item",
						"source_warehouse": "_Test Warehouse - _TC",
						"required_qty": 5,
						"transferred_qty": 2,
					}
				],
			}
		).insert(ignore_mandatory=True)

		materials = get_raw_materials([job_card.name])

		self.assertEqual(list(materials), [job_card.name])
		self.assertEqual(len(materials[job_card.name]), 1)
		material = materials[job_card.name][0]
		self.assertEqual(material.item_code, "_Test Item")
		self.assertEqual(material.required_qty, 5)
		self.assertEqual(material.transferred_qty, 2)
		self.assertEqual(material.source_warehouse, "_Test Warehouse - _TC")

	def test_validate_timings(self):
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 11:00:00", "2013-02-02 19:00:00"
		)
		check_if_within_operating_hours(
			"_Test Workstation 1", "Operation 1", "2013-02-02 10:00:00", "2013-02-02 20:00:00"
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			NotInWorkingHoursError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-02 05:00:00",
			"2013-02-02 20:00:00",
		)
		self.assertRaises(
			WorkstationHolidayError,
			check_if_within_operating_hours,
			"_Test Workstation 1",
			"Operation 1",
			"2013-02-01 10:00:00",
			"2013-02-02 20:00:00",
		)

	def test_update_bom_operation_rate(self):
		operations = [
			{
				"operation": "Test Operation A",
				"workstation": "_Test Workstation A",
				"hour_rate_rent": 300,
				"time_in_mins": 60,
			},
			{
				"operation": "Test Operation B",
				"workstation": "_Test Workstation B",
				"hour_rate_rent": 1000,
				"time_in_mins": 60,
			},
		]

		for row in operations:
			make_workstation(row)
			make_operation(row)

		test_routing_operations = [
			{"operation": "Test Operation A", "workstation": "_Test Workstation A", "time_in_mins": 60},
			{"operation": "Test Operation B", "workstation": "_Test Workstation A", "time_in_mins": 30},
		]
		routing_doc = create_routing(routing_name="Routing Test", operations=test_routing_operations)
		bom_doc = setup_bom(item_code="_Testing Item", routing=routing_doc.name, currency="INR")
		w1 = frappe.get_doc("Workstation", "_Test Workstation A")
		# resets values
		w1.hour_rate_rent = 300
		w1.hour_rate_labour = 0
		w1.save()
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 300)
		self.assertEqual(bom_doc.operations[0].hour_rate, 300)
		w1.hour_rate_rent = 250
		w1.save()
		# updating after setting new rates in workstations
		bom_doc.update_cost()
		bom_doc.reload()
		self.assertEqual(w1.hour_rate, 250)
		self.assertEqual(bom_doc.operations[0].hour_rate, 250)
		self.assertEqual(bom_doc.operations[1].hour_rate, 250)

		# hour_rate propagation must also refresh operating_cost (hour_rate * time_in_mins / 60)
		# on the Routing's BOM Operation rows; the 30-min op exercises the arithmetic.
		for operation, expected_operating_cost in (("Test Operation A", 250), ("Test Operation B", 125)):
			hour_rate, operating_cost = frappe.db.get_value(
				"BOM Operation",
				{"parent": routing_doc.name, "parenttype": "Routing", "operation": operation},
				["hour_rate", "operating_cost"],
			)
			self.assertEqual(hour_rate, 250)
			self.assertEqual(operating_cost, expected_operating_cost)

<<<<<<< HEAD
=======
	def test_manufacture_uses_operating_cost_recorded_on_the_work_order(self):
		from frappe.utils import add_to_date, now

		from erpnext.manufacturing.doctype.routing.test_routing import setup_operations
		from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_wo_stock_entry
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry as make_test_entry

		workstation = make_workstation(workstation_name="_Test WS Recorded Cost", hour_rate_rent=600)
		operations = [
			{"operation": "_Test Op Recorded Cost", "workstation": workstation.name, "time_in_mins": 6}
		]
		setup_operations(operations)
		fg_item = make_item("_Test FG Recorded Cost", {"is_stock_item": 1}).name
		rm_item = make_item("_Test RM Recorded Cost", {"is_stock_item": 1}).name
		routing = create_routing(routing_name="Recorded Cost Route", operations=operations)
		bom = setup_bom(
			item_code=fg_item, routing=routing.name, raw_materials=[rm_item], source_warehouse="Stores - _TC"
		)
		make_test_entry(item_code=rm_item, target="Stores - _TC", qty=10, basic_rate=50)

		work_order = make_wo_order_test_record(
			production_item=fg_item, bom_no=bom.name, qty=10, skip_transfer=1, source_warehouse="Stores - _TC"
		)
		job_card = frappe.get_doc("Job Card", {"work_order": work_order.name})
		from_time = add_to_date(now(), days=1)
		job_card.append(
			"time_logs",
			{"from_time": from_time, "to_time": add_to_date(from_time, minutes=60), "completed_qty": 10},
		)
		job_card.submit()

		workstation.reload()
		workstation.workstation_costs[0].operating_cost = 1200
		workstation.save()

		entry = frappe.get_doc(make_wo_stock_entry(work_order.name, "Manufacture", 10))
		entry.insert()
		recorded_cost = frappe.db.get_value(
			"Work Order Operation", {"parent": work_order.name}, "actual_operating_cost"
		)
		self.assertAlmostEqual(recorded_cost, 600, delta=1)
		self.assertEqual(
			sum(row.amount for row in entry.additional_costs if row.has_operating_cost), recorded_cost
		)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 0, "allow_overtime": 0})
	def test_job_card_starts_in_the_next_shift_of_the_same_day(self):
		shifts = [("13:00:00", "17:00:00"), ("08:00:00", "12:00:00")]
		self.assertEqual(
			schedule_one_operation("_Test WS Shift Early", shifts, 60, "2031-03-03 06:00:00"),
			[("2031-03-03 08:00:00", "2031-03-03 09:00:00")],
		)
		self.assertEqual(
			schedule_one_operation("_Test WS Shift Break", shifts, 60, "2031-03-03 12:30:00"),
			[("2031-03-03 13:00:00", "2031-03-03 14:00:00")],
		)
		self.assertEqual(
			schedule_one_operation("_Test WS Shift Order", shifts, 360, "2031-03-03 08:00:00"),
			[("2031-03-03 08:00:00", "2031-03-03 12:00:00"), ("2031-03-03 13:00:00", "2031-03-03 15:00:00")],
		)

	@change_settings(
		"Manufacturing Settings",
		{"disable_capacity_planning": 0, "allow_overtime": 0, "mins_between_operations": 10},
	)
	def test_start_moved_into_a_shift_is_checked_for_overlap(self):
		shifts = [("08:00:00", "17:00:00")]
		self.assertEqual(
			schedule_one_operation("_Test WS Shift Overlap", shifts, 60, "2031-03-05 08:00:00"),
			[("2031-03-05 08:00:00", "2031-03-05 09:00:00")],
		)
		self.assertEqual(
			schedule_one_operation("_Test WS Shift Overlap", shifts, 60, "2031-03-05 06:00:00"),
			[("2031-03-05 09:10:00", "2031-03-05 10:10:00")],
		)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 0, "allow_overtime": 0})
	def test_disabled_working_hours_are_not_used(self):
		shifts = [("08:00:00", "12:00:00"), ("13:00:00", "17:00:00", 0)]
		self.assertEqual(
			schedule_one_operation("_Test WS Disabled Shift", shifts, 360, "2031-03-03 08:00:00"),
			[("2031-03-03 08:00:00", "2031-03-03 12:00:00"), ("2031-03-04 08:00:00", "2031-03-04 10:00:00")],
		)
		self.assertEqual(
			frappe.db.get_value("Workstation", "_Test WS Disabled Shift", "total_working_hours"), 4
		)

	@change_settings("Manufacturing Settings", {"disable_capacity_planning": 0, "allow_overtime": 0})
	def test_operation_planned_times_span_all_scheduled_slots(self):
		job_card = make_scheduled_job_card(
			"_Test WS Multi Day", [("08:00:00", "12:00:00")], 360, "2031-03-03 08:00:00"
		)
		self.assertEqual(
			frappe.db.get_value(
				"Work Order Operation",
				job_card.operation_id,
				["planned_start_time", "planned_end_time"],
				as_dict=True,
			),
			{
				"planned_start_time": get_datetime("2031-03-03 08:00:00"),
				"planned_end_time": get_datetime("2031-03-04 10:00:00"),
			},
		)

	@change_settings(
		"Manufacturing Settings",
		{"disable_capacity_planning": 0, "allow_overtime": 0, "allow_production_on_holidays": 0},
	)
	def test_holidays_are_skipped_without_working_hours_and_with_overtime(self):
		holiday_list = make_test_holiday_list("_Test WS Holiday List", ["2031-03-03"])
		self.assertEqual(
			schedule_one_operation("_Test WS Holiday No Shift", [], 60, "2031-03-03 08:00:00", holiday_list),
			[("2031-03-04 08:00:00", "2031-03-04 09:00:00")],
		)

		frappe.db.set_single_value("Manufacturing Settings", "allow_overtime", 1)
		self.assertEqual(
			schedule_one_operation(
				"_Test WS Holiday Overtime",
				[("08:00:00", "17:00:00")],
				60,
				"2031-03-03 08:00:00",
				holiday_list,
			),
			[("2031-03-04 08:00:00", "2031-03-04 09:00:00")],
		)

	def test_complete_job_books_the_qty_once_on_an_open_card(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		job_card = make_scheduled_job_card("_Test WS Complete Job", [], 60, "2031-03-03 08:00:00", qty=10)
		workstation = frappe.get_doc("Workstation", "_Test WS Complete Job")
		other_workstation = make_workstation(workstation_name="_Test WS Complete Job Other")

		first = make_employee("ws-operator-1@example.com", company="_Test Company")
		second = make_employee("ws-operator-2@example.com", company="_Test Company")
		self.assertRaises(
			frappe.ValidationError, other_workstation.start_job, job_card.name, "2031-03-03 10:00:00", first
		)
		workstation.start_job(job_card.name, "2031-03-03 10:00:00", first)
		workstation.start_job(job_card.name, "2031-03-03 10:00:00", second)
		workstation.complete_job(job_card.name, 5, "2031-03-03 11:00:00")

		self.assertEqual(frappe.db.get_value("Job Card", job_card.name, "total_completed_qty"), 5)
		self.assertRaises(
			frappe.ValidationError, workstation.start_job, job_card.name, "2031-03-03 13:00:00", first
		)

	def test_oee_counts_process_loss_once(self):
		from frappe.tests.classes.context_managers import freeze_time
		from frappe.utils import add_to_date, now_datetime, nowdate

		from erpnext.manufacturing.page.shop_floor.shop_floor import get_workstation_oee

		with freeze_time(f"{nowdate()} 12:00:00", tick=True):
			start = add_to_date(now_datetime(), minutes=-90)
			job_card = make_scheduled_job_card(
				"_Test WS OEE", [("00:00:00", "23:59:00")], 60, start.strftime("%Y-%m-%d %H:%M:%S"), qty=10
			)
			job_card.append(
				"time_logs",
				{"from_time": start, "to_time": add_to_date(start, minutes=60), "completed_qty": 8},
			)
			job_card.save()
			job_card.submit()
			self.assertEqual(job_card.process_loss_qty, 2)

			oee = get_workstation_oee("_Test WS OEE")
			self.assertEqual(oee["quality"], 80)
			self.assertEqual(oee["performance"], 100)

	def test_oee_leaves_out_loss_of_work_done_on_another_day(self):
		from frappe.tests.classes.context_managers import freeze_time
		from frappe.utils import add_to_date, now_datetime, nowdate

		from erpnext.manufacturing.page.shop_floor.shop_floor import get_workstation_oee

		with freeze_time(f"{nowdate()} 12:00:00", tick=True):
			shifts = [("00:00:00", "23:59:00")]
			yesterday = add_to_date(now_datetime(), days=-1, hours=-2)
			old_card = make_scheduled_job_card(
				"_Test WS OEE Days", shifts, 6, yesterday.strftime("%Y-%m-%d %H:%M:%S"), qty=10
			)
			old_card.append(
				"time_logs",
				{"from_time": yesterday, "to_time": add_to_date(yesterday, minutes=60), "completed_qty": 8},
			)
			old_card.save()
			old_card.submit()

			start = add_to_date(now_datetime(), minutes=-90)
			card = make_scheduled_job_card(
				"_Test WS OEE Days", shifts, 6, start.strftime("%Y-%m-%d %H:%M:%S"), qty=10
			)
			card.append(
				"time_logs",
				{"from_time": start, "to_time": add_to_date(start, minutes=60), "completed_qty": 5},
			)
			card.save()

			self.assertEqual(get_workstation_oee("_Test WS OEE Days")["performance"], 50)

	def test_oee_counts_run_time_once_for_a_crew(self):
		from frappe.tests.classes.context_managers import freeze_time
		from frappe.utils import add_to_date, now_datetime, nowdate

		from erpnext.manufacturing.page.shop_floor.shop_floor import get_workstation_oee
		from erpnext.setup.doctype.employee.test_employee import make_employee

		first = make_employee("oee-operator-1@example.com", company="_Test Company")
		second = make_employee("oee-operator-2@example.com", company="_Test Company")
		with freeze_time(f"{nowdate()} 12:00:00", tick=True):
			shifts = [("08:00:00", "16:00:00")]
			start = add_to_date(now_datetime(), minutes=-90)
			card = make_scheduled_job_card(
				"_Test WS OEE Crew", shifts, 6, start.strftime("%Y-%m-%d %H:%M:%S"), qty=10
			)
			end = add_to_date(start, minutes=60)
			card.append("time_logs", {"employee": first, "from_time": start, "to_time": end})
			card.append(
				"time_logs", {"employee": second, "from_time": start, "to_time": end, "completed_qty": 10}
			)
			card.save()

			oee = get_workstation_oee("_Test WS OEE Crew")
			self.assertEqual(oee["availability"], 12.5)
			self.assertEqual(oee["performance"], 100)

>>>>>>> a6d3092 (test: operation planned start for a multi-day scheduled job card)

def make_workstation(*args, **kwargs):
	args = args if args else kwargs
	if isinstance(args, tuple):
		args = args[0]

	args = frappe._dict(args)

	workstation_name = args.workstation_name or args.workstation
	if not frappe.db.exists("Workstation", workstation_name):
		doc = frappe.get_doc({"doctype": "Workstation", "workstation_name": workstation_name})
		doc.hour_rate_rent = args.get("hour_rate_rent")
		doc.hour_rate_labour = args.get("hour_rate_labour")
		doc.workstation_type = args.get("workstation_type")
		doc.insert()

		return doc

	return frappe.get_doc("Workstation", workstation_name)
