# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import itertools

import frappe

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	make_closing_entries,
)
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


def execute():
	# clear balances, they will be recalculated
	frappe.db.truncate("Account Closing Balance")

	pcv_list = get_period_closing_vouchers()

	if pcv_list:
		gl_entries = get_gl_entries(pcv_list)

		for _, pcvs in itertools.groupby(pcv_list, key=lambda pcv: (pcv.company, pcv.period_start_date)):
			process_grouped_pcvs(list(pcvs), gl_entries)


def process_grouped_pcvs(pcvs, gl_entries):
	pl_account_entries = []
	closing_account_entries = []
	first_pcv = pcvs[0]

	for pcv in pcvs:
		pcv_entries = gl_entries.get(pcv.name) or []
		for entry in pcv_entries:
			entry["closing_date"] = first_pcv.period_end_date
			entry["period_closing_voucher"] = first_pcv.name
			entry["voucher_no"] = first_pcv.name

			list_to_update = (
				pl_account_entries if entry.account != pcv.closing_account_head else closing_account_entries
			)
			list_to_update.append(entry)

	# hacky!!
	if to_cancel := pcvs[1:]:
		to_cancel = [pcv.name for pcv in to_cancel]

		# update voucher number
		gle_to_update = [entry.name for entry in closing_account_entries + pl_account_entries]
		frappe.db.set_value(
			"GL Entry",
			{
				"name": ("in", gle_to_update),
				"voucher_no": ("in", to_cancel),
			},
			"voucher_no",
			first_pcv.name,
			update_modified=False,
		)

		# mark as cancelled
		frappe.db.set_value(
			"Period Closing Voucher",
			{"name": ("in", to_cancel)},
			"docstatus",
			2,
			update_modified=False,
		)

	pcv_doc = frappe.get_doc("Period Closing Voucher", first_pcv.name)
	pcv_doc.pl_accounts_reverse_gle = pl_account_entries
	pcv_doc.closing_account_gle = closing_account_entries
	closing_entries = pcv_doc.get_account_closing_balances()
	make_closing_entries(closing_entries, pcv_doc.name, pcv_doc.company, pcv_doc.period_end_date)


def get_period_closing_vouchers():
	return frappe.db.get_all(
		"Period Closing Voucher",
		fields=["name", "closing_account_head", "period_start_date", "period_end_date", "company"],
		filters={"docstatus": 1},
		order_by="period_start_date asc, period_end_date desc",
	)


def get_gl_entries(pcv_list):
	gl_entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_no": ("in", [pcv.name for pcv in pcv_list]), "is_cancelled": 0},
		fields=get_gle_fields(),
		update={"is_period_closing_voucher_entry": 1},
	)

	return {k: list(v) for k, v in itertools.groupby(gl_entries, key=lambda gle: gle.voucher_no)}


def get_gle_fields():
	return [
		"name",
		"company",
		"posting_date",
		"account",
		"account_currency",
		"debit",
		"credit",
		"debit_in_account_currency",
		"credit_in_account_currency",
		"voucher_no",
		# default dimension fields
		"cost_center",
		"finance_book",
		"project",
		# accounting dimensions
		*get_accounting_dimensions(),
	]
