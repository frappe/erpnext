import frappe

def execute():
	for name in frappe.db.sql_list("""select name from `tabSalary Slip` where docstatus=1"""):
		salary_slip = frappe.get_doc("Salary Slip", name)
		salary_slip.set_salary_component_type_earning()
		salary_slip.set_salary_component_type_deduction()
	