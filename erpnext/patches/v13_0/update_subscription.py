# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "subscription")
	frappe.reload_doc("accounts", "doctype", "subscription_invoice")
	frappe.reload_doc("accounts", "doctype", "subscription_plan")

	if frappe.db.has_column("Subscription", "customer"):
		subscription = frappe.qb.DocType("Subscription")
		(
			frappe.qb.update(subscription)
			.set(subscription.start_date, subscription.start)
			.set(subscription.party_type, "Customer")
			.set(subscription.party, subscription.customer)
			.set(subscription.sales_tax_template, subscription.tax_template)
			.where(subscription.party.isnull() | (subscription.party == ""))
		).run()

	frappe.db.set_value(
		"Subscription Invoice",
		{"document_type": ["in", ["", None]]},
		"document_type",
		"Sales Invoice",
		update_modified=False,
	)

	price_determination_map = {
		"Fixed rate": "Fixed Rate",
		"Based on price list": "Based On Price List",
	}

	for key, value in price_determination_map.items():
		frappe.db.set_value(
			"Subscription Plan",
			{"price_determination": key},
			"price_determination",
			value,
			update_modified=False,
		)
