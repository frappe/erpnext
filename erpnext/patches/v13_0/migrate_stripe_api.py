import frappe


def execute():
	subscription_plans = frappe.get_all(
		"Subscription Plan", fields=["name", "payment_plan_id"]
	)

	for plan in subscription_plans:
		frappe.db.set_value(
			"Subscription Plan",
			plan.name,
			"product_price_id",
			plan.payment_plan_id,
			update_modified=False
		)
