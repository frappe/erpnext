import frappe


def execute():
	frappe.reload_doc("accounts", "doctype", "overdue_payment")
	frappe.reload_doc("accounts", "doctype", "dunning")

	# Migrate schema of all uncancelled dunnings
	filters = {"docstatus": ("!=", 2)}

	all_dunnings = frappe.get_all("Dunning", filters=filters, pluck="name")

	for dunning_name in all_dunnings:
		dunning = frappe.get_doc("Dunning", dunning_name)
		if not dunning.sales_invoice:
			# nothing we can do
			continue

		if dunning.overdue_payments:
			# something's already here, doesn't need patching
			continue

		payment_schedules = frappe.get_all(
			"Payment Schedule",
			filters={"parent": dunning.sales_invoice},
			fields=[
				"parent as sales_invoice",
				"name as payment_schedule",
				"payment_term",
				"due_date",
				"invoice_portion",
				"payment_amount",
				# at the time of creating this dunning, the full amount was outstanding
				"payment_amount as outstanding",
				"'0' as paid_amount",
				"discounted_amount",
			],
		)

		dunning.extend("overdue_payments", payment_schedules)
		dunning.validate()

		dunning.flags.ignore_validate_update_after_submit = True
		dunning.save()
