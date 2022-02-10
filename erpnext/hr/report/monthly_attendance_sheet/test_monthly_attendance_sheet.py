import frappe
from frappe.utils import get_datetime

from erpnext.hr.doctype.attendance.attendance import mark_attendance
from erpnext.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import execute
from erpnext.tests.utils import ERPNextTestCase


class TestMonthlyAttendanceSheet(ERPNextTestCase):
	def setUp(self):
		frappe.db.delete('Leave Application')
		frappe.db.delete('Attendance')

	def test_monthly_attendance_sheet_report(self):
		current_month = get_datetime().month
		current_year = get_datetime().year
		today = get_datetime().date()

		employee = "_T-Employee-00001"
		mark_attendance(employee, today, 'Absent')

		filters = frappe._dict({
			'month': current_month,
			'year': current_year,
			'company': '_Test Company',
		})
		report = execute(filters=filters)
		employees = report[1][0]
		datasets = report[3]['data']['datasets']
		absent = datasets[0]['values']

		self.assertIn(employee, employees)
		self.assertEqual(sum(absent), 1)
