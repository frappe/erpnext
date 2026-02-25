import frappe


def execute():
	default_exchange_gain_loss_accounts = frappe.get_all(
		"Company",
		filters={"exchange_gain_loss_account": ["!=", ""]},
		pluck="exchange_gain_loss_account",
	)

	if not default_exchange_gain_loss_accounts:
		return

	payment_entry = frappe.qb.DocType("Payment Entry")
	payment_entry_deduction = frappe.qb.DocType("Payment Entry Deduction")

	frappe.qb.update(payment_entry_deduction).set(payment_entry_deduction.is_exchange_gain_loss, 1).join(
		payment_entry,
	).on(payment_entry.name == payment_entry_deduction.parent).where(
		(payment_entry.paid_to_account_currency != payment_entry.paid_from_account_currency)
		& (payment_entry_deduction.account.isin(default_exchange_gain_loss_accounts))
	).run()
