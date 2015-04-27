# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import getdate

test_records = frappe.get_test_records('Task')

from erpnext.projects.doctype.task.task import CircularReferenceError

class TestTask(unittest.TestCase):
	def test_circular_refereence(self):
		task1 =  frappe.new_doc('Task')
		task1.update({
			"status": "Open", 
			"subject": "_Test Task 3"
		})
		task1.save()
		
		task2 =  frappe.new_doc('Task')
		task2.update({
			"status": "Open", 
			"subject": "_Test Task 4",
			"depends_on": task1.name
		})
		task2.save()
		
		task3 =  frappe.new_doc('Task')
		task3.update({
			"status": "Open", 
			"subject": "_Test Task 5",
			"depends_on": task2.name
		})
		task3.save()
		
		task1.update({
			"depends_on": task3.name
		})
		self.assertRaises(CircularReferenceError, task1.save)
		
	def test_reschedule_dependent_task(self):
		task1 =  frappe.new_doc('Task')
		task1.update({
			"status": "Open", 
			"subject": "_Test Task 6",
			"exp_start_date": "2015-1-1",
			"exp_end_date": "2015-1-10"
		})
		task1.save()
		
		task2 =  frappe.new_doc('Task')
		task2.update({
			"status": "Open", 
			"subject": "_Test Task 7",
			"exp_start_date": "2015-1-11",
			"exp_end_date": "2015-1-15",
			"depends_on": task1.name
		})
		task2.save()
		
		task3 =  frappe.new_doc('Task')
		task3.update({
			"status": "Open", 
			"subject": "_Test Task 5",
			"exp_start_date": "2015-1-16",
			"exp_end_date": "2015-1-18",
			"depends_on": task2.name
		})
		task3.save()
		
		task1.update({
			"exp_end_date": "2015-1-20"
		})
		task1.save()
		
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"), getdate('2015-1-21'))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"), getdate('2015-1-25'))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"), getdate('2015-1-26'))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"), getdate('2015-1-28'))
		
		time_log = frappe.new_doc('Time Log')
		time_log.update({
			"from_time": "2015-1-1",
			"to_time": "2015-1-20",
			"task": task1.name
		})
		time_log.submit()
		
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"), getdate('2015-1-21'))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"), getdate('2015-1-25'))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"), getdate('2015-1-26'))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"), getdate('2015-1-28'))
		
		time_log.cancel()
		
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"), getdate('2015-1-21'))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"), getdate('2015-1-25'))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"), getdate('2015-1-26'))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"), getdate('2015-1-28'))
		