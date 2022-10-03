import frappe


def execute():
	frappe.reload_doc("loan_management", "doctype", "loan")
	loan = frappe.qb.DocType("Loan")

	for company in frappe.get_all("Company", pluck="name"):
		default_cost_center = frappe.db.get_value("Company", company, "cost_center")
		frappe.qb.update(loan).set(loan.cost_center, default_cost_center).where(
			loan.company == company
		).run()
