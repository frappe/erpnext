# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import unittest

import datetime
from frappe.utils import now_datetime, now
from erpnext.projects.doctype.time_log.time_log import OverlapError, NotSubmittedError, NegativeHoursError
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError, NotInWorkingHoursError
from erpnext.manufacturing.doctype.production_order.test_production_order import make_prod_order_test_record


class TestTimeLog(unittest.TestCase):
	def test_duplication(self):
		tl1 = make_time_log_test_record(user= "test@example.com", employee= "_T-Employee-0002", simulate= True)

		tl2 = make_time_log_test_record(user= "test@example.com", employee= "_T-Employee-0002",
			from_time= tl1.from_time, to_time= tl1.to_time, do_not_save= 1)

		self.assertRaises(OverlapError, tl2.insert)
		
		tl3 = make_time_log_test_record(user= "test@example.com", employee= "_T-Employee-0002",
			from_time= tl1.from_time - datetime.timedelta(hours=1), 
			to_time= tl1.to_time + datetime.timedelta(hours=1), do_not_save= 1)

		self.assertRaises(OverlapError, tl3.insert)
		
		tl4 = make_time_log_test_record(user= "test@example.com", employee= "_T-Employee-0002",
			from_time= tl1.from_time + datetime.timedelta(minutes=20), 
			to_time= tl1.to_time + datetime.timedelta(minutes=30), do_not_save= 1)

		self.assertRaises(OverlapError, tl4.insert)
		
		make_time_log_test_record(user= "test@example.com", employee= "_T-Employee-0002",
			from_time= tl1.to_time, 
			to_time= tl1.to_time + datetime.timedelta(hours=1))

	def test_production_order_status(self):
		prod_order = make_prod_order_test_record(item= "_Test FG Item 2", qty= 1, do_not_submit= True)
		prod_order.set_production_order_operations()
		prod_order.save()

		time_log = make_time_log_test_record(for_manufacturing= 1, production_order= prod_order.name, qty= 1,
			employee= "_T-Employee-0003", do_not_save= True, simulate=1)

		self.assertRaises(NotSubmittedError, time_log.save)

	def test_time_log_on_holiday(self):
		prod_order = make_prod_order_test_record(item= "_Test FG Item 2", qty= 1,
			planned_start_date= now(), do_not_save= True)
		prod_order.set_production_order_operations()
		prod_order.save()
		prod_order.submit()

		time_log = make_time_log_test_record(from_time= "2013-02-01 10:00:00", to_time= "2013-02-01 20:00:00",
			for_manufacturing= 1, production_order= prod_order.name, qty= 1,
			operation= prod_order.operations[0].operation, operation_id= prod_order.operations[0].name,
			workstation= "_Test Workstation 1", do_not_save= True)

		self.assertRaises(WorkstationHolidayError , time_log.save)

		time_log.update({
			"from_time": "2013-02-02 09:00:00",
			"to_time": "2013-02-02 20:00:00"
		})
		self.assertRaises(NotInWorkingHoursError , time_log.save)

		time_log.from_time= "2013-02-02 10:30:00"
		time_log.save()
		time_log.submit()
		time_log.cancel()

	def test_negative_hours(self):
		time_log = make_time_log_test_record(to_time= now_datetime() + datetime.timedelta(minutes=-1),
			employee="_T-Employee-0006",do_not_save= True)
		self.assertRaises(NegativeHoursError, time_log.save)

	def test_default_activity_cost(self):
		activity_type = frappe.get_doc("Activity Type", "_Test Activity Type")
		activity_type.billing_rate = 20
		activity_type.costing_rate = 15
		activity_type.save()

		project_name = "_Test Project for Activity Type"

		frappe.db.sql("delete from `tabTime Log` where project=%s or employee='_T-Employee-0002'", project_name)
		frappe.delete_doc("Project", project_name)
		project = frappe.get_doc({"doctype": "Project", "project_name": project_name}).insert()

		make_time_log_test_record(employee="_T-Employee-0002", hours=2,
			activity_type = "_Test Activity Type", project = project.name)

		project = frappe.get_doc("Project", project.name)
		self.assertTrue(project.total_costing_amount, 30)
		self.assertTrue(project.total_billing_amount, 40)

	def test_total_activity_cost_for_project(self):
		frappe.db.sql("""delete from `tabTask` where project = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabProject` where name = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabTime Log` where name = "_Test Project 1" """)

		if not frappe.db.exists('Activity Cost', {"activity_type": "_Test Activity Type"}):
			activity_cost = frappe.get_doc({
				"doctype": "Activity Cost",
				"employee": "_T-Employee-0002",
				"activity_type": "_Test Activity Type",
				"billing_rate": 100,
				"costing_rate": 50
			})
			activity_cost.insert()

		frappe.get_doc({
			"project_name": "_Test Project 1",
			"doctype": "Project",
			"tasks" :
				[{ "title": "_Test Project Task 1", "status": "Open" }]
		}).save()

		task_name = frappe.db.get_value("Task",{"project": "_Test Project 1"})

		time_log = make_time_log_test_record(employee="_T-Employee-0002", hours=2,
			task=task_name, simulate=1)
		self.assertEqual(time_log.costing_rate, 50)
		self.assertEqual(time_log.costing_amount, 100)
		self.assertEqual(time_log.billing_rate, 100)
		self.assertEqual(time_log.billing_amount, 200)

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 200)

		time_log2 = make_time_log_test_record(employee="_T-Employee-0002",
			hours=2, task= task_name, from_time = now_datetime() + datetime.timedelta(hours= 3), simulate=1)
		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 400)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 400)

		time_log2.cancel()

		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 200)
		time_log.cancel()

test_ignore = ["Time Log Batch", "Sales Invoice"]

def make_time_log_test_record(**args):
	args = frappe._dict(args)

	time_log = frappe.new_doc("Time Log")

	time_log.from_time = args.from_time or now_datetime()
	time_log.hours = args.hours or 1
	time_log.to_time = args.to_time or time_log.from_time + datetime.timedelta(hours= time_log.hours)

	time_log.project = args.project
	time_log.task = args.task
	time_log.for_manufacturing = args.for_manufacturing
	time_log.production_order = args.production_order
	time_log.operation = args.operation
	time_log.operation_id = args.operation_id
	time_log.workstation = args.workstation
	time_log.completed_qty = args.completed_qty
	time_log.activity_type = args.activity_type or "_Test Activity Type"
	time_log.billable = args.billable or 1
	time_log.employee = args.employee
	time_log.user = args.user

	if not args.do_not_save:
		if args.simulate:
			while True:
				try:
					time_log.save()
					break
				except OverlapError:
					time_log.from_time = time_log.from_time + datetime.timedelta(minutes=10)
					time_log.to_time = time_log.from_time + datetime.timedelta(hours= time_log.hours)
		else:
			time_log.save()
		if not args.do_not_submit:
			time_log.submit()

	return time_log
