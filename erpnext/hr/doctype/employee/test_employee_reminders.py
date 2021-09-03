# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from datetime import timedelta

import frappe
from frappe.utils import getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.hr_settings.hr_settings import set_proceed_with_frequency_change


class TestEmployeeReminders(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		from erpnext.hr.doctype.holiday_list.test_holiday_list import make_holiday_list

		# Create a test holiday list
		test_holiday_dates = cls.get_test_holiday_dates()
		test_holiday_list = make_holiday_list(
			'TestHolidayRemindersList',
			holiday_dates=[
				{'holiday_date': test_holiday_dates[0], 'description': 'test holiday1'},
				{'holiday_date': test_holiday_dates[1], 'description': 'test holiday2'},
				{'holiday_date': test_holiday_dates[2], 'description': 'test holiday3', 'weekly_off': 1},
				{'holiday_date': test_holiday_dates[3], 'description': 'test holiday4'},
				{'holiday_date': test_holiday_dates[4], 'description': 'test holiday5'},
				{'holiday_date': test_holiday_dates[5], 'description': 'test holiday6'},
			],
			from_date=getdate()-timedelta(days=10),
			to_date=getdate()+timedelta(weeks=5)
		)

		# Create a test employee
		test_employee = frappe.get_doc(
			'Employee',
			make_employee('test@gopher.io', company="_Test Company")
		)

		# Attach the holiday list to employee
		test_employee.holiday_list = test_holiday_list.name
		test_employee.save()

		# Attach to class
		cls.test_employee = test_employee
		cls.test_holiday_dates = test_holiday_dates

	@classmethod
	def get_test_holiday_dates(cls):
		today_date = getdate()
		return [
			today_date,
			today_date-timedelta(days=4),
			today_date-timedelta(days=3),
			today_date+timedelta(days=1),
			today_date+timedelta(days=3),
			today_date+timedelta(weeks=3)
		]

	def setUp(self):
		# Clear Email Queue
		frappe.db.sql("delete from `tabEmail Queue`")

	def test_is_holiday(self):
		from erpnext.hr.doctype.employee.employee import is_holiday

		self.assertTrue(is_holiday(self.test_employee.name))
		self.assertTrue(is_holiday(self.test_employee.name, date=self.test_holiday_dates[1]))
		self.assertFalse(is_holiday(self.test_employee.name, date=getdate()-timedelta(days=1)))

		# Test weekly_off holidays
		self.assertTrue(is_holiday(self.test_employee.name, date=self.test_holiday_dates[2]))
		self.assertFalse(is_holiday(self.test_employee.name, date=self.test_holiday_dates[2], only_non_weekly=True))

		# Test with descriptions
		has_holiday, descriptions = is_holiday(self.test_employee.name, with_description=True)
		self.assertTrue(has_holiday)
		self.assertTrue('test holiday1' in descriptions)

	def test_birthday_reminders(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		employee.date_of_birth = "1992" + frappe.utils.nowdate()[4:]
		employee.company_email = "test@example.com"
		employee.company = "_Test Company"
		employee.save()

		from erpnext.hr.doctype.employee.employee_reminders import (
			get_employees_who_are_born_today,
			send_birthday_reminders,
		)

		employees_born_today = get_employees_who_are_born_today()
		self.assertTrue(employees_born_today.get("_Test Company"))

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.send_birthday_reminders = 1
		hr_settings.save()

		send_birthday_reminders()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue("Subject: Birthday Reminder" in email_queue[0].message)

	def test_work_anniversary_reminders(self):
		employee = frappe.get_doc("Employee", frappe.db.sql_list("select name from tabEmployee limit 1")[0])
		employee.date_of_joining = "1998" + frappe.utils.nowdate()[4:]
		employee.company_email = "test@example.com"
		employee.company = "_Test Company"
		employee.save()

		from erpnext.hr.doctype.employee.employee_reminders import (
			get_employees_having_an_event_today,
			send_work_anniversary_reminders,
		)

		employees_having_work_anniversary = get_employees_having_an_event_today('work_anniversary')
		self.assertTrue(employees_having_work_anniversary.get("_Test Company"))

		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.send_work_anniversary_reminders = 1
		hr_settings.save()

		send_work_anniversary_reminders()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue("Subject: Work Anniversary Reminder" in email_queue[0].message)

	def test_send_holidays_reminder_in_advance(self):
		from erpnext.hr.doctype.employee.employee_reminders import send_holidays_reminder_in_advance
		from erpnext.hr.utils import get_holidays_for_employee

		# Get HR settings and enable advance holiday reminders
		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.send_holiday_reminders = 1
		set_proceed_with_frequency_change()
		hr_settings.frequency = 'Weekly'
		hr_settings.save()

		holidays = get_holidays_for_employee(
					self.test_employee.get('name'),
					getdate(), getdate() + timedelta(days=3),
					only_non_weekly=True,
					raise_exception=False
				)

		send_holidays_reminder_in_advance(
			self.test_employee.get('name'),
			holidays
		)

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertEqual(len(email_queue), 1)

	def test_advance_holiday_reminders_monthly(self):
		from erpnext.hr.doctype.employee.employee_reminders import send_reminders_in_advance_monthly

		# Get HR settings and enable advance holiday reminders
		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.send_holiday_reminders = 1
		set_proceed_with_frequency_change()
		hr_settings.frequency = 'Monthly'
		hr_settings.save()

		send_reminders_in_advance_monthly()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue(len(email_queue) > 0)

	def test_advance_holiday_reminders_weekly(self):
		from erpnext.hr.doctype.employee.employee_reminders import send_reminders_in_advance_weekly

		# Get HR settings and enable advance holiday reminders
		hr_settings = frappe.get_doc("HR Settings", "HR Settings")
		hr_settings.send_holiday_reminders = 1
		hr_settings.frequency = 'Weekly'
		hr_settings.save()

		send_reminders_in_advance_weekly()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue(len(email_queue) > 0)
