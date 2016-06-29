from __future__ import unicode_literals
import frappe
from frappe.utils import random_string

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
