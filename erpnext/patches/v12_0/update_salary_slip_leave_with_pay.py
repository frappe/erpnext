import frappe
from frappe.utils import cint


def execute():
	frappe.reload_doc("hr", "doctype", "salary_slip")
	salary_slips = frappe.get_all("Salary Slip")
	for d in salary_slips:
		doc = frappe.get_doc("Salary Slip", d.name)
		holidays = doc.get_holidays_for_employee(doc.start_date, doc.end_date)
		leave_count = doc.get_leave_count(holidays, cint(doc.total_working_days), doc.joining_date, doc.relieving_date)
		if leave_count.leave_with_pay:
			doc.db_set('leave_with_pay', leave_count.leave_with_pay)
		doc.clear_cache()
