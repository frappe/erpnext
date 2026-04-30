import frappe


def execute():
	for gateway_account in frappe.get_list("Payment Gateway Account", fields=["name", "payment_account"]):
		company = frappe.db.get_value("Account", gateway_account.payment_account, "company")
		frappe.db.set_value("Payment Gateway Account", gateway_account.name, "company", company)
