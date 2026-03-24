import frappe


def execute():
	frappe.reload_doc("setup", "doctype", "currency_exchange")
	currency_exchange = frappe.qb.DocType("Currency Exchange")
	(
		frappe.qb.update(currency_exchange)
		.set(currency_exchange.for_buying, 1)
		.set(currency_exchange.for_selling, 1)
	).run()
