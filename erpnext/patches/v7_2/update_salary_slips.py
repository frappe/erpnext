import frappe
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_month_details
from frappe.utils import cint

def execute():
	frappe.reload_doctype('Salary Slip')
	if not frappe.db.has_column('Salary Slip', 'fiscal_year'):
		return

	salary_slips = frappe.db.sql("""select month, name, fiscal_year from `tabSalary Slip`
				where (month is not null and month != '') and
				start_date is null and end_date is null and docstatus != 2""", as_dict=True)

	for salary_slip in salary_slips:
		if not cint(salary_slip.month):
			continue
		get_start_end_date = get_month_details(salary_slip.fiscal_year, cint(salary_slip.month))
		start_date = get_start_end_date['month_start_date']
		end_date = get_start_end_date['month_end_date']
		frappe.db.sql("""update `tabSalary Slip` set start_date = %s, end_date = %s where name = %s""",
		(start_date, end_date, salary_slip.name))