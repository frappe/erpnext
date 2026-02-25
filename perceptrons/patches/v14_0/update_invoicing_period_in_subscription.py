import frappe


def execute():
	subscription = frappe.qb.DocType("Subscription")
	frappe.qb.update(subscription).set(
		subscription.generate_invoice_at, "Beginning of the current subscription period"
	).where(subscription.generate_invoice_at_period_start == 1).run()
