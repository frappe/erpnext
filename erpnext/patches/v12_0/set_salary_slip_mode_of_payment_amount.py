import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "salary_slip")

	frappe.db.sql("""
		update `tabSalary Slip`
		set no_mode_amount = rounded_total
		where salary_mode not in ('Bank', 'Cheque', 'Cash')
	""")

	frappe.db.sql("""
		update `tabSalary Slip`
		set bank_amount = rounded_total
		where salary_mode = 'Bank'
	""")

	frappe.db.sql("""
		update `tabSalary Slip`
		set cheque_amount = rounded_total
		where salary_mode = 'Cheque'
	""")

	frappe.db.sql("""
		update `tabSalary Slip`
		set cash_amount = rounded_total
		where salary_mode = 'Cash'
	""")
