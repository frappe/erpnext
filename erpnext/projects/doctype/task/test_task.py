# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from erpnext.projects.doctype.task.task import CircularReferenceError


class TestTask(unittest.TestCase):
	def test_circular_reference(self):
		task1 = create_task("_Test Task 1", add_days(nowdate(), -15), add_days(nowdate(), -10))
		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)

		task1.reload()
		task1.append("depends_on", {
			"task": task3.name
		})

		self.assertRaises(CircularReferenceError, task1.save)

		task1.set("depends_on", [])
		task1.save()

		task4 = create_task("_Test Task 4", nowdate(), add_days(nowdate(), 15), task1.name)

		task3.append("depends_on", {
			"task": task4.name
		})

	def test_reschedule_dependent_task(self):
		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		task1 = create_task("_Test Task 1", nowdate(), add_days(nowdate(), 10))

		task2 = create_task("_Test Task 2", add_days(nowdate(), 11), add_days(nowdate(), 15), task1.name)
		task2.get("depends_on")[0].project = project
		task2.save()

		task3 = create_task("_Test Task 3", add_days(nowdate(), 11), add_days(nowdate(), 15), task2.name)
		task3.get("depends_on")[0].project = project
		task3.save()

		task1.update({
			"exp_end_date": add_days(nowdate(), 20)
		})
		task1.save()

		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_start_date"),
			getdate(add_days(nowdate(), 21)))
		self.assertEqual(frappe.db.get_value("Task", task2.name, "exp_end_date"),
			getdate(add_days(nowdate(), 25)))

		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_start_date"),
			getdate(add_days(nowdate(), 26)))
		self.assertEqual(frappe.db.get_value("Task", task3.name, "exp_end_date"),
			getdate(add_days(nowdate(), 30)))

	def test_close_assignment(self):
		if not frappe.db.exists("Task", "Test Close Assignment"):
			task = frappe.new_doc("Task")
			task.subject = "Test Close Assignment"
			task.insert()

		def assign():
			from frappe.desk.form import assign_to
			assign_to.add({
				"assign_to": ["test@example.com"],
				"doctype": task.doctype,
				"name": task.name,
				"description": "Close this task"
			})

		def get_owner_and_status():
			return frappe.db.get_value("ToDo",
				filters={"reference_type": task.doctype, "reference_name": task.name,
					"description": "Close this task"},
				fieldname=("allocated_to", "status"), as_dict=True)

		assign()
		todo = get_owner_and_status()
		self.assertEqual(todo.allocated_to, "test@example.com")
		self.assertEqual(todo.status, "Open")

		# assignment should be
		task.load_from_db()
		task.status = "Completed"
		task.save()
		todo = get_owner_and_status()
		self.assertEqual(todo.allocated_to, "test@example.com")
		self.assertEqual(todo.status, "Closed")

	def test_overdue(self):
		task = create_task("Testing Overdue", add_days(nowdate(), -10), add_days(nowdate(), -5))

		from erpnext.projects.doctype.task.task import set_tasks_as_overdue
		set_tasks_as_overdue()

		self.assertEqual(frappe.db.get_value("Task", task.name, "status"), "Overdue")

	def test_task_with_boq(self):
		task = create_task("_Test Task 2")
		task.from_bom = frappe.db.get_value("BOM", {"item": "_Test FG Item",
			"is_default": 1, "docstatus": 1})
		task.project_warehouse = 'Stores - _TC'
		task.company = '_Test Company'
		task.project = ''
		task.get_items()
		task.save()

		row = task.items[0]
		self.assertEqual(row.item_code, '_Test Item')
		self.assertEqual(row.qty, 1)
		self.assertEqual(row.estimated_cost, flt(row.qty) * flt(row.basic_rate))

		row = task.items[1]
		self.assertEqual(row.item_code, '_Test Item Home Desktop 100')
		self.assertEqual(row.qty, 2)
		self.assertEqual(row.estimated_cost, flt(row.qty) * flt(row.basic_rate))

		# Back updating transfers and issues
		from erpnext.projects.doctype.task.task import make_stock_entry_mi, make_stock_entry_mt
		mi = make_stock_entry_mi(task.name)
		mi.items[1].qty = 1
		mi.submit()

		# Both items have the same default warehouse
		for item in mi.items:
			self.assertEqual(item.s_warehouse, task.items[0].warehouse)
			self.assertEqual(item.t_warehouse, None)

		task.reload()

		for item in task.items:
			self.assertEqual(item.issued, 1)

		# Test for fetching only remaining required items in MT
		mt = make_stock_entry_mt(task.name)
		self.assertEqual(len(mt.items), 1)
		self.assertEqual(mt.items[0].qty, 1)
		self.assertEqual(mt.items[0].s_warehouse, task.items[0].warehouse)
		self.assertEqual(mt.items[0].t_warehouse, task.project_warehouse)
		mt.submit()

		task.reload()
		self.assertEqual(task.items[1].transferred, 1)

		frappe.db.rollback()

def create_task(subject, start=None, end=None, depends_on=None, project=None, parent_task=None, is_group=0, is_template=0, begin=0, duration=0, save=True):
	if not frappe.db.exists("Task", subject):
		task = frappe.new_doc('Task')
		task.status = "Open"
		task.subject = subject
		task.exp_start_date = start or nowdate()
		task.exp_end_date = end or nowdate()
		task.project = project or None if is_template else frappe.get_value("Project", {"project_name": "_Test Project"})
		task.is_template = is_template
		task.start = begin
		task.duration = duration
		task.is_group = is_group
		task.parent_task = parent_task
		if save:
			task.save()
	else:
		task = frappe.get_doc("Task", subject)

	if depends_on:
		task.append("depends_on", {
			"task": depends_on
		})
		if save:
			task.save()
	return task
