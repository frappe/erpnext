import frappe

from erpnext.accounts.general_ledger import make_reverse_gl_entries


def execute():
	frappe.reload_doc("accounts", "doctype", "overdue_payment")
	frappe.reload_doc("accounts", "doctype", "dunning")

	# Migrate schema of all uncancelled dunnings
	filters = {"docstatus": ("!=", 2)}

	can_edit_accounts_after = get_accounts_closing_date()
	if can_edit_accounts_after:
		# Get dunnings after the date when accounts were frozen/closed
		filters["posting_date"] = (">", can_edit_accounts_after)

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

		# Reverse entries only if dunning is submitted and not resolved
		if dunning.docstatus == 1 and dunning.status != "Resolved":
			# With the new logic, dunning amount gets recorded as additional income
			# at time of payment. We don't want to record the dunning amount twice,
			# so we reverse previous GL Entries that recorded the dunning amount at
			# time of submission of the Dunning.
			make_reverse_gl_entries(voucher_type="Dunning", voucher_no=dunning.name)


def get_accounts_closing_date():
	"""Get the date when accounts were frozen/closed"""
	accounts_frozen_till = frappe.db.get_single_value(
		"Accounts Settings", "acc_frozen_upto"
	)  # always returns datetime.date

	period_closing_date = frappe.db.get_value(
		"Period Closing Voucher", {"docstatus": 1}, "period_end_date", order_by="period_end_date desc"
	)

	# Set most recent frozen/closing date as filter
	if accounts_frozen_till and period_closing_date:
		can_edit_accounts_after = max(accounts_frozen_till, period_closing_date)
	else:
		can_edit_accounts_after = accounts_frozen_till or period_closing_date

	return can_edit_accounts_after
