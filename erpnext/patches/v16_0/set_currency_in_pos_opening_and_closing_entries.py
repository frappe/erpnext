import frappe


def execute():
	profile_currencies = frappe.get_all("POS Profile", fields=["name", "currency"], as_list=True)
	for doctype in ("POS Opening Entry", "POS Closing Entry"):
		entry = frappe.qb.DocType(doctype)
		for pos_profile, currency in profile_currencies:
			(
				frappe.qb.update(entry)
				.set(entry.currency, currency)
				.where(
					(entry.pos_profile == pos_profile) & (entry.currency.isnull() | (entry.currency == ""))
				)
				.run()
			)
