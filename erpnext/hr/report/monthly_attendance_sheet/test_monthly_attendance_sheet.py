import frappe
from dateutil.relativedelta import relativedelta

from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from erpnext.hr.doctype.attendance.attendance import mark_attendance
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import execute


class TestMonthlyAttendanceSheet(FrappeTestCase):
	def setUp(self):
		self.employee = make_employee("test_employee@example.com")
		frappe.db.delete('Attendance', {'employee': self.employee})

	def test_monthly_attendance_sheet_report(self):
		now = now_datetime()
		previous_month = now.month - 1
		month_first = now.replace(day=1).replace(month=previous_month).date()

		company = frappe.db.get_value('Employee', self.employee, 'company')
		entries = 7

		for day in range(0, entries*3, 3):
			mark_attendance(self.employee, month_first + relativedelta(days=day), 'Present')
			mark_attendance(self.employee, month_first + relativedelta(days=day+1), 'Absent')
			mark_attendance(self.employee, month_first + relativedelta(days=day+2), 'On Leave')

		filters = frappe._dict({
			'month': previous_month,
			'year': now.year,
			'company': company,
		})
		report = execute(filters=filters)
		employees = report[1][0]
		datasets = report[3]['data']['datasets']
		absent = datasets[0]['values']
		present = datasets[1]['values']
		leaves = datasets[2]['values']

		self.assertIn(self.employee, employees)
		self.assertEqual(sum(present), entries)
		self.assertEqual(sum(absent), entries)
		self.assertEqual(sum(leaves), entries)
