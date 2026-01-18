import frappe

from erpnext.accounts.utils import get_advance_payment_doctypes

DOCTYPE = "Payment Ledger Entry"


def execute():
	"""
	Description:
	Set against_voucher as entry for Payment Ledger Entry against advance vouchers.
	"""
	advance_payment_doctypes = get_advance_payment_doctypes()

	if not advance_payment_doctypes:
		return
	ple = frappe.qb.DocType(DOCTYPE)

	(
		frappe.qb.update(ple)
		.set(ple.against_voucher_type, ple.voucher_type)
		.set(ple.against_voucher_no, ple.voucher_no)
		.where(ple.against_voucher_type.isin(advance_payment_doctypes))
		.run()
	)
