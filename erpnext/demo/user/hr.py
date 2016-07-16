from __future__ import unicode_literals
import frappe
import random
from frappe.utils import random_string
from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.projects.doctype.timesheet.timesheet import make_salary_slip, make_sales_invoice
from frappe.utils.make_random import how_many, get_random

def work():
	frappe.set_user(frappe.db.get_global('demo_hr_user'))
	year, month = frappe.flags.current_date.strftime("%Y-%m").split("-")

	# process payroll
	if not frappe.db.get_value("Salary Slip", {"month": month, "fiscal_year": year}):
		process_payroll = frappe.get_doc("Process Payroll", "Process Payroll")
		process_payroll.company = frappe.flags.company
		process_payroll.month = month
		process_payroll.fiscal_year = year
		process_payroll.create_sal_slip()
		process_payroll.submit_salary_slip()
		r = process_payroll.make_journal_entry(frappe.get_value('Account',
			{'account_name': 'Salary'}))

		journal_entry = frappe.get_doc(r)
		journal_entry.cheque_no = random_string(10)
		journal_entry.cheque_date = frappe.flags.current_date
		journal_entry.posting_date = frappe.flags.current_date
		journal_entry.insert()
		journal_entry.submit()
	
	if frappe.db.get_global('demo_hr_user'):
		make_timesheet_records()

def get_timesheet_based_salary_slip_employee():
	return frappe.get_all('Salary Structure', fields = ["distinct employee as name"],
		filters = {'salary_slip_based_on_timesheet': 1})
	
def make_timesheet_records():
	employees = get_timesheet_based_salary_slip_employee()
	for employee in employees:
		ts = make_timesheet(employee.name, simulate = True, billable = 1, activity_type=get_random("Activity Type"))

		rand = random.random()
		if rand >= 0.3:
			make_salary_slip_for_timesheet(ts.name)

		rand = random.random()
		if rand >= 0.2:
			make_sales_invoice_for_timesheet(ts.name)

def make_salary_slip_for_timesheet(name):
	salary_slip = make_salary_slip(name)
	salary_slip.insert()
	salary_slip.submit()

def make_sales_invoice_for_timesheet(name):
	sales_invoice = make_sales_invoice(name)
	sales_invoice.customer = get_random("Customer")
	sales_invoice.append('items', {
		'item_code': get_random_item(),
		'qty': 1,
		'rate': 1000
	})
	sales_invoice.set_missing_values()
	sales_invoice.calculate_taxes_and_totals()
	sales_invoice.insert()
	sales_invoice.submit()

def get_random_item():
	return frappe.db.sql_list(""" select name from `tabItem` where
		has_variants = 0 order by rand() limit 1""")[0]
