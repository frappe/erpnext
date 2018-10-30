# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe
import erpnext
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
		self.assertTrue("Subject: Birthday Reminder" in email_queue[0].message)

	def test_delete_events(self):
		from frappe.utils import today
		employee = frappe.get_doc({
			"doctype":"Employee",
			"first_name": "Test Delete",
			"employee_number": "12345",
			"gender": "Male",
			"date_of_birth": "1995-07-20",
			"date_of_joining": today(),
		}).insert()

		ev = frappe.get_doc({
			"doctype":"Event",
			"subject": "Test Delete Event",
			"starts_on": today(),
			"event_type": "Public",
			'event_participants': [{
				"reference_doctype": employee.doctype,
				"reference_docname": employee.name
			}]
		}).insert()

		self.assertTrue(frappe.db.exists('Event', ev.name))

		# delete employee should delete event
		frappe.delete_doc('Employee', employee.name)
		self.assertFalse(frappe.db.exists('Event', ev.name))

def make_employee(user):
	if not frappe.db.get_value("User", user):
		frappe.get_doc({
			"doctype": "User",
			"email": user,
			"first_name": user,
			"new_password": "password",
			"roles": [{"doctype": "Has Role", "role": "Employee"}]
		}).insert()

	if not frappe.db.get_value("Employee", {"user_id": user}):
		employee = frappe.get_doc({
			"doctype": "Employee",
			"naming_series": "EMP-",
			"first_name": user,
			"company": erpnext.get_default_company(),
			"user_id": user,
			"date_of_birth": "1990-05-08",
			"date_of_joining": "2013-01-01",
			"department": frappe.get_all("Department", fields="name")[0].name,
			"gender": "Female",
			"company_email": user,
			"prefered_contact_email": "Company Email",
			"prefered_email": user,
			"status": "Active",
			"employment_type": "Intern"
		}).insert()
		return employee.name
	else:
		return frappe.get_value("Employee", {"employee_name":user}, "name")
