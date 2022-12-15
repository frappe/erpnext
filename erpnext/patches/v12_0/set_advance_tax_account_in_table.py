import frappe


def execute():
	if not frappe.db.has_column("Company", "advance_tax_account"):
		return

	frappe.reload_doc("accounts", "doctype", "advance_tax_account")
	frappe.reload_doc("setup", "doctype", "company")

	companies = [d.name for d in frappe.get_all("Company")]
	for name in companies:
		advance_tax_account = frappe.db.get_value("Company", name, "advance_tax_account")
		if advance_tax_account:
			doc = frappe.get_doc("Company", name)
			row = doc.append("advance_tax_accounts", {"account_head": advance_tax_account})
			row.db_insert()
