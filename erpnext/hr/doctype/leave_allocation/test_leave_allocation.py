from __future__ import unicode_literals
import frappe
import unittest
from frappe.utils import getdate

class TestLeaveAllocation(unittest.TestCase):
	def test_overlapping_allocation(self):
		frappe.db.sql("delete from `tabLeave Allocation`")
				
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		leaves = [
			{
				"doctype": "Leave Allocation",
				"__islocal": 1,
				"employee": employee.name,
				"employee_name": employee.employee_name,
				"leave_type": "_Test Leave Type",
				"from_date": getdate("2015-10-01"),
				"to_date": getdate("2015-10-31"),
				"new_leaves_allocated": 5,
				"docstatus": 1			
			},
			{
				"doctype": "Leave Allocation",
				"__islocal": 1,
				"employee": employee.name,
				"employee_name": employee.employee_name,
				"leave_type": "_Test Leave Type",
				"from_date": getdate("2015-09-01"),
				"to_date": getdate("2015-11-30"),
				"new_leaves_allocated": 5			
			}
		]

		frappe.get_doc(leaves[0]).save()
		self.assertRaises(frappe.ValidationError, frappe.get_doc(leaves[1]).save)
		
	def test_invalid_period(self):		
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		
		d = frappe.get_doc({
			"doctype": "Leave Allocation",
			"__islocal": 1,
			"employee": employee.name,
			"employee_name": employee.employee_name,
			"leave_type": "_Test Leave Type",
			"from_date": getdate("2015-09-30"),
			"to_date": getdate("2015-09-1"),
			"new_leaves_allocated": 5			
		})
		
		#invalid period
		self.assertRaises(frappe.ValidationError, d.save)
	
	def test_allocated_leave_days_over_period(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		d = frappe.get_doc({
			"doctype": "Leave Allocation",
			"__islocal": 1,
			"employee": employee.name,
			"employee_name": employee.employee_name,
			"leave_type": "_Test Leave Type",
			"from_date": getdate("2015-09-1"),
			"to_date": getdate("2015-09-30"),
			"new_leaves_allocated": 35			
		})
		
		#allocated leave more than period 
		self.assertRaises(frappe.ValidationError, d.save)
		
test_dependencies = ["Employee", "Leave Type"]