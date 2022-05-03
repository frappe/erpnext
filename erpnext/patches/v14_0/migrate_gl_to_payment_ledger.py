import frappe
from frappe import qb
from frappe.query_builder.functions import IfNull

from erpnext.accounts.doctype.payment_ledger_entry.payment_ledger_entry import (
	get_payment_ledger_entries,
)


def execute():

	# migrate against_voucher column data to payment ledger
	if frappe.db.exists("DocType", "Payment Ledger Entry"):
		gle = qb.DocType("GL Entry")
		query = (
			qb.from_(gle)
			.select(
				gle.posting_date,
				gle.account,
				gle.voucher_type,
				gle.voucher_no,
				gle.against_voucher_type,
				gle.against_voucher,
				gle.debit,
				gle.credit,
			)
			.where(
				(gle.is_cancelled == 0)
				& (IfNull(gle.against_voucher, "") != "")
				& (gle.voucher_no != gle.against_voucher)
			)
			.orderby(gle.posting_date)
		)
		docs = query.run(as_dict=True)
		ple_docs = get_payment_ledger_entries(docs)
		for ple in ple_docs:
			ple.save()
