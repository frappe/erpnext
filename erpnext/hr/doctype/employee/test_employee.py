# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe
import unittest
import frappe.utils

test_records = frappe.get_test_records('Employee')

class TestEmployee(unittest.TestCase):
	def test_birthday_reminders(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		employee.date_of_birth = "1992" + frappe.utils.nowdate()[4:]
		employee.company_email = "test@example.com"
		employee.save()

		from erpnext.hr.doctype.employee.employee import get_employees_who_are_born_today, send_birthday_reminders

		self.assertTrue(employee.name in [e.name for e in get_employees_who_are_born_today()])

		frappe.db.sql("delete from `tabEmail Queue`")

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.stop_birthday_reminders = 0
		hr_settings.save()

		send_birthday_reminders()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue("Subject: Birthday Reminder for {0}".format(employee.employee_name) \
			in email_queue[0].message)

