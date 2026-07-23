import frappe

VALUE_MAP = {
	"End of the current subscription period": "Postpaid (bill at period end)",
	"Beginning of the current subscription period": "Prepaid (bill at period start)",
	"Days before the current subscription period": "Bill N days before period start",
}


def execute():
	subscription = frappe.qb.DocType("Subscription")
	for old_value, new_value in VALUE_MAP.items():
		(
			frappe.qb.update(subscription)
			.set(subscription.generate_invoice_at, new_value)
			.where(subscription.generate_invoice_at == old_value)
		).run()
