# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LedgerHealth(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checked_on: DF.Datetime | None
		debit_credit_mismatch: DF.Check
		general_and_payment_ledger_mismatch: DF.Check
		name: DF.Int | None
		voucher_no: DF.Data | None
		voucher_type: DF.Data | None
	# end: auto-generated types

	pass


def update_ledger_health(check, vouchers, run_date, scan):
	still_reported, stale = get_kept_and_stale_ledger_health(check, vouchers, scan)

	if stale:
		frappe.db.delete("Ledger Health", {"name": ("in", stale)})

	if still_reported:
		ledger_health = frappe.qb.DocType("Ledger Health")
		frappe.qb.update(ledger_health).set(ledger_health.checked_on, run_date).where(
			ledger_health.name.isin(list(still_reported.values()))
		).run()

	for voucher_type, voucher_no in vouchers - still_reported.keys():
		doc = frappe.new_doc("Ledger Health")
		doc.update({"voucher_type": voucher_type, "voucher_no": voucher_no, check: 1, "checked_on": run_date})
		doc.save()


def get_kept_and_stale_ledger_health(check, vouchers, scan):
	still_reported, extra_records = {}, {}
	for row in frappe.get_all(
		"Ledger Health", filters={check: 1}, fields=["name", "voucher_type", "voucher_no"], order_by="name"
	):
		voucher = (row.voucher_type, row.voucher_no)
		if voucher in vouchers and voucher not in still_reported:
			still_reported[voucher] = row.name
		else:
			extra_records.setdefault(voucher, []).append(row.name)

	rechecked = vouchers | get_vouchers_in_scan(extra_records.keys() - vouchers, scan)
	stale = [name for voucher in extra_records.keys() & rechecked for name in extra_records[voucher]]
	return still_reported, stale


def get_vouchers_in_scan(vouchers, scan):
	if not vouchers or not scan.companies:
		return set()

	gle = frappe.qb.DocType("GL Entry")
	scanned = (
		frappe.qb.from_(gle)
		.select(gle.voucher_type, gle.voucher_no)
		.distinct()
		.where(
			gle.company.isin(scan.companies)
			& gle.posting_date.between(scan.from_date, scan.to_date)
			& gle.voucher_no.isin([voucher_no for _voucher_type, voucher_no in vouchers])
		)
	).run()
	return {tuple(row) for row in scanned} & vouchers
