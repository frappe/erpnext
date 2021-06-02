# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_datetime
from erpnext.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
from erpnext.payroll.doctype.gratuity.gratuity import get_salary_structure
from frappe.model.document import Document
from pprint import pprint

class OvertimeSlip(Document):

	@frappe.whitelist()
	def get_emp_and_overtime_details(self):
		overtime_based_on = frappe.db.get_single_value("Payroll Settings", "overtime_based_on")
		records = []
		if overtime_based_on == "Attendance":
			records = self.get_attendance_record()
		elif overtime_based_on == "Timesheet":
			records = self.get_timesheet_record()
		else:
			frappe.throw(_('Select "Calculate Overtime Hours Based On" in Payroll Settings'))

		if len(records):
			self.create_overtime_details_row(records)
		else:
			frappe.throw(_("No {0} records found for Overtime").format(overtime_based_on))

	def create_overtime_details_row(self, records):
		pprint(records)


	def get_attendance_record(self):
		records = frappe.db.sql("""SELECT overtime_duration, employee, name, attendance_date, overtime_type
			FROM `TabAttendance`
			WHERE
				attendance_date >= %s AND attendance_date <= %s
				AND employee = %s
				AND docstatus = 1 AND status= 'Present'
				AND (
					overtime_duration IS NOT NULL OR overtime_duration != '00:00:00.000000'
				)
		""", (get_datetime(self.from_date), get_datetime(self.to_date), self.employee), as_dict=1)

		return records


@frappe.whitelist()
def get_frequency_and_dates(employee, date):
	print(date)
	salary_structure = get_salary_structure(employee)
	if salary_structure:
		payroll_frequency = frappe.db.get_value('Salary Structure', salary_structure, 'payroll_frequency')
		date_details = get_start_end_dates(payroll_frequency, date, frappe.db.get_value('Employee', employee, 'company'))
		print(date_details)
		return [date_details, payroll_frequency]
	else:
		frappe.throw(_("No Salary Structure Assignment found for Employee: {0}").format(employee))


