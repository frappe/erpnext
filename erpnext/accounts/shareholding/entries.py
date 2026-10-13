# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, flt, now_datetime

from erpnext.accounts.shareholding.locking import lock_company


def create_ledger_entry(
	transaction,
	share_folio,
	quantity_change,
	posting_date,
	treasury_cost_change=0,
	is_reversal=False,
	reversal_of=None,
):
	posting_sequence = get_next_posting_sequence(transaction.company, posting_date)
	entry = frappe.get_doc(
		{
			"doctype": "Share Ledger Entry",
			"share_transaction": transaction.name,
			"source_doctype": transaction.doctype,
			"source_name": transaction.name,
			"posting_key": f"share-transaction:{transaction.name}:{share_folio}:{reversal_of or 'movement'}",
			"recorded_at": now_datetime(),
			"capital_change": quantity_change * flt(transaction.face_value_per_share),
			"transaction_type": transaction.transaction_type,
			"company": transaction.company,
			"posting_date": posting_date,
			"posting_sequence": posting_sequence,
			"share_class": transaction.share_class,
			"share_folio": share_folio,
			"from_share_number": transaction.from_share_number,
			"to_share_number": transaction.to_share_number,
			"quantity_change": quantity_change,
			"currency": transaction.currency,
			"face_value_per_share": transaction.face_value_per_share,
			"treasury_cost_change": treasury_cost_change,
			"is_reversal": 1 if is_reversal else 0,
			"reversal_of": reversal_of,
		}
	)
	entry.flags.from_share_transaction = True
	entry.insert(ignore_permissions=True)
	return entry


def get_next_posting_sequence(company, posting_date):
	lock_company(company)
	sequence = frappe.db.get_value(
		"Share Ledger Entry",
		{"company": company, "posting_date": posting_date},
		"posting_sequence",
		order_by="posting_sequence desc",
		for_update=True,
	)
	return cint(sequence) + 1
