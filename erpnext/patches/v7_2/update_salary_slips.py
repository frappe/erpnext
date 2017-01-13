import frappe
from erpnext.hr.doctype.process_payroll.process_payroll import get_month_details

def execute():
	ss_columns = frappe.db.get_table_columns("Salary Slip")
	if "fiscal_year" not in ss_columns or "month" not in ss_columns:
		return
		
	salary_slips = frappe.db.sql("""select fiscal_year, month, name from `tabSalary Slip` 
				where (month is not null and month != '') 
				and (fiscal_year is not null and fiscal_year != '') and
				(start_date is null  or start_date = '') and 
				(end_date is null  or end_date = '') and docstatus != 2""", as_dict=1)

	for salary_slip in salary_slips:
		get_start_end_date = get_month_details(salary_slip.fiscal_year, salary_slip.month)
		start_date = get_start_end_date['month_start_date']
		end_date = get_start_end_date['month_end_date']
		frappe.db.sql("""update `tabSalary Slip` set start_date = %s, end_date = %s where name = %s""",
		(start_date, end_date, salary_slip.name))