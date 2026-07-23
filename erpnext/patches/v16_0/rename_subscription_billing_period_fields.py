import frappe


def execute():
	"""Move billing-period data to the renamed fields.

	`current_invoice_start/end` used to hold the open (next) billing period and now
	holds the actual current invoice period, while the open period moved to
	`next_billing_period_start/end`.
	"""
	columns = set(frappe.db.get_table_columns("Subscription"))
	subscription = frappe.qb.DocType("Subscription")

	if {"next_billing_period_start", "next_billing_period_end"} <= columns:
		(
			frappe.qb.update(subscription)
			.set(subscription.next_billing_period_start, subscription.current_invoice_start)
			.set(subscription.next_billing_period_end, subscription.current_invoice_end)
		).run()

	if {"current_invoice_from_date", "current_invoice_to_date"} <= columns:
		(
			frappe.qb.update(subscription)
			.set(subscription.current_invoice_start, subscription.current_invoice_from_date)
			.set(subscription.current_invoice_end, subscription.current_invoice_to_date)
		).run()
