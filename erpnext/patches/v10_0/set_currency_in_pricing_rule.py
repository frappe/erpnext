import frappe


def execute():
	frappe.reload_doctype("Pricing Rule")

	currency = frappe.db.get_default("currency")
	for doc in frappe.get_all("Pricing Rule", fields=["company", "name"]):
		if doc.company:
			currency = frappe.get_cached_value("Company", doc.company, "default_currency")

		frappe.db.sql("""update `tabPricing Rule` set currency = %s where name = %s""", (currency, doc.name))
