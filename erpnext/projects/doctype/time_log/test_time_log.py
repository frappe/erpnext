# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import unittest

from erpnext.projects.doctype.time_log.time_log import OverlapError
from erpnext.projects.doctype.time_log.time_log import NotSubmittedError
from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.manufacturing.doctype.workstation.workstation import NotInWorkingHoursError
from erpnext.manufacturing.doctype.production_order.test_production_order import make_prod_order_test_record


class TestTimeLog(unittest.TestCase):
	def test_duplication(self):
		frappe.db.sql("delete from `tabTime Log`")

		tl1 = frappe.get_doc(frappe.copy_doc(test_records[0]))
		tl1.user = "test@example.com"
		tl1.insert()

		tl2 = frappe.get_doc(frappe.copy_doc(test_records[0]))
		tl2.user = "test@example.com"

		self.assertRaises(OverlapError, tl2.insert)

		frappe.db.sql("delete from `tabTime Log`")

	def test_production_order_status(self):
		prod_order = make_prod_order_test_record(item="_Test FG Item 2", qty=1, do_not_submit=True)
		prod_order.set_production_order_operations()
		prod_order.save()

		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"for_manufacturing": 1,
			"production_order": prod_order.name,
			"qty": 1,
			"from_time": "2014-12-26 00:00:00",
			"to_time": "2014-12-26 00:00:00"
		})

		self.assertRaises(NotSubmittedError, time_log.save)

	def test_time_log_on_holiday(self):
		prod_order = make_prod_order_test_record(item="_Test FG Item 2", qty=1, 
			planned_start_date="2014-11-25 00:00:00", do_not_save=True)
		prod_order.set_production_order_operations()
		prod_order.save()
		prod_order.submit()

		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"for_manufacturing": 1,
			"production_order": prod_order.name,
			"operation": prod_order.operations[0].operation,
			"operation_id": prod_order.operations[0].name,
			"qty": 1,
			"activity_type": "_Test Activity Type",
			"from_time": "2013-02-01 10:00:00",
			"to_time": "2013-02-01 20:00:00",
			"workstation": "_Test Workstation 1"
		})
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
		frappe.db.sql("delete from `tabTime Log`")
		test_time_log = frappe.new_doc("Time Log")
		test_time_log.activity_type = "Communication"
		test_time_log.from_time = "2013-01-01 11:00:00.000000"
		test_time_log.to_time = "2013-01-01 10:00:00.000000"
		self.assertRaises(frappe.ValidationError, test_time_log.save)
		frappe.db.sql("delete from `tabTime Log`")
		
	def test_total_activity_cost_for_project(self):
		frappe.db.sql("""delete from `tabTask` where project = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabProject` where name = "_Test Project 1" """)
		frappe.db.sql("""delete from `tabActivity Cost` where employee = "_T-Employee-0001" and activity_type = "_Test Activity Type" """)
		
		activity_cost = frappe.new_doc('Activity Cost')
		activity_cost.update({
			"employee": "_T-Employee-0001",
			"employee_name": "_Test Employee",
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
		
		time_log = frappe.get_doc({
			 "activity_type": "_Test Activity Type",
			 "docstatus": 1,
			 "doctype": "Time Log",
			 "from_time": "2013-02-02 09:00:00.000000",
			 "to_time": "2013-02-02 11:00:00.000000",
			 "employee": "_T-Employee-0001",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "billable": 1
		})
		time_log.save()
		self.assertEqual(time_log.costing_rate, 50)
		self.assertEqual(time_log.costing_amount, 100)
		self.assertEqual(time_log.billing_rate, 100)
		self.assertEqual(time_log.billing_amount, 200)
		time_log.submit()
		
		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 200)
		
		time_log2 = frappe.get_doc({
			 "activity_type": "_Test Activity Type",
			 "docstatus": 1,
			 "doctype": "Time Log",
			 "from_time": "2013-02-03 09:00:00.000000",
			 "to_time": "2013-02-03 11:00:00.000000",
			 "employee": "_T-Employee-0001",
			 "project": "_Test Project 1",
			 "task": task_name,
			 "billable": 1
		})
		time_log2.save()
		
		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 400)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 400)
		
		time_log2.cancel()
		
		self.assertEqual(frappe.db.get_value("Task", task_name, "total_billing_amount"), 200)
		self.assertEqual(frappe.db.get_value("Project", "_Test Project 1", "total_billing_amount"), 200)
		
test_records = frappe.get_test_records('Time Log')
test_ignore = ["Time Log Batch", "Sales Invoice"]
