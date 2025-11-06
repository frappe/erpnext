# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
from datetime import timedelta

import frappe
from frappe import qb
from frappe.model.document import Document
from frappe.query_builder.functions import Count, Max, Min, Sum
from frappe.utils import add_days, flt, get_datetime
from frappe.utils.scheduler import is_scheduler_inactive

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	make_closing_entries,
)


class ProcessPeriodClosingVoucher(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.process_period_closing_voucher_detail.process_period_closing_voucher_detail import (
			ProcessPeriodClosingVoucherDetail,
		)

		amended_from: DF.Link | None
		bs_closing_balance: DF.JSON | None
		normal_balances: DF.Table[ProcessPeriodClosingVoucherDetail]
		p_l_closing_balance: DF.JSON | None
		parent_pcv: DF.Link
		status: DF.Literal["Queued", "Running", "Paused", "Completed", "Cancelled"]
		z_opening_balances: DF.Table[ProcessPeriodClosingVoucherDetail]
	# end: auto-generated types

	def validate(self):
		self.status = "Queued"
		self.populate_processing_tables()

	def populate_processing_tables(self):
		self.generate_pcv_dates()
		self.generate_opening_balances_dates()

	def get_dates(self, start, end):
		return [start + timedelta(days=x) for x in range((end - start).days + 1)]

	def generate_pcv_dates(self):
		self.normal_balances = []
		pcv = frappe.get_doc("Period Closing Voucher", self.parent_pcv)

		dates = self.get_dates(get_datetime(pcv.period_start_date), get_datetime(pcv.period_end_date))
		for x in dates:
			self.append(
				"normal_balances",
				{"processing_date": x, "status": "Queued", "report_type": "Profit and Loss"},
			)
			self.append(
				"normal_balances", {"processing_date": x, "status": "Queued", "report_type": "Balance Sheet"}
			)

	def generate_opening_balances_dates(self):
		self.z_opening_balances = []

		pcv = frappe.get_doc("Period Closing Voucher", self.parent_pcv)
		if pcv.is_first_period_closing_voucher():
			gl = qb.DocType("GL Entry")
			min = qb.from_(gl).select(Min(gl.posting_date)).where(gl.company.eq(pcv.company)).run()[0][0]
			max = qb.from_(gl).select(Max(gl.posting_date)).where(gl.company.eq(pcv.company)).run()[0][0]

			dates = self.get_dates(get_datetime(min), get_datetime(max))
			for x in dates:
				self.append(
					"z_opening_balances",
					{"processing_date": x, "status": "Queued", "report_type": "Balance Sheet"},
				)

	def on_submit(self):
		start_pcv_processing(self.name)

	def on_cancel(self):
		cancel_pcv_processing(self.name)


@frappe.whitelist()
def start_pcv_processing(docname: str):
	if frappe.db.get_value("Process Period Closing Voucher", docname, "status") in ["Queued", "Running"]:
		frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Running")
		if normal_balances := frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": docname, "status": "Queued"},
			fields=["processing_date", "report_type", "parentfield"],
			order_by="parentfield, idx, processing_date",
			limit=4,
		):
			if not is_scheduler_inactive():
				for x in normal_balances:
					frappe.db.set_value(
						"Process Period Closing Voucher Detail",
						{
							"processing_date": x.processing_date,
							"parent": docname,
							"report_type": x.report_type,
							"parentfield": x.parentfield,
						},
						"status",
						"Running",
					)
					frappe.enqueue(
						method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
						queue="long",
						timeout="3600",
						is_async=True,
						enqueue_after_commit=True,
						docname=docname,
						date=x.processing_date,
						report_type=x.report_type,
						parentfield=x.parentfield,
					)
		else:
			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


@frappe.whitelist()
def pause_pcv_processing(docname: str):
	ppcv = qb.DocType("Process Period Closing Voucher")
	qb.update(ppcv).set(ppcv.status, "Paused").where(ppcv.name.eq(docname)).run()

	if queued_dates := frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Queued"},
		pluck="name",
	):
		ppcvd = qb.DocType("Process Period Closing Voucher Detail")
		qb.update(ppcvd).set(ppcvd.status, "Paused").where(ppcvd.name.isin(queued_dates)).run()


@frappe.whitelist()
def cancel_pcv_processing(docname: str):
	ppcv = qb.DocType("Process Period Closing Voucher")
	qb.update(ppcv).set(ppcv.status, "Cancelled").where(ppcv.name.eq(docname)).run()

	if queued_dates := frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Queued"},
		pluck="name",
	):
		ppcvd = qb.DocType("Process Period Closing Voucher Detail")
		qb.update(ppcvd).set(ppcvd.status, "Cancelled").where(ppcvd.name.isin(queued_dates)).run()


@frappe.whitelist()
def resume_pcv_processing(docname: str):
	ppcv = qb.DocType("Process Period Closing Voucher")
	qb.update(ppcv).set(ppcv.status, "Running").where(ppcv.name.eq(docname)).run()

	if paused_dates := frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Paused"},
		pluck="name",
	):
		ppcvd = qb.DocType("Process Period Closing Voucher Detail")
		qb.update(ppcvd).set(ppcvd.status, "Queued").where(ppcvd.name.isin(paused_dates)).run()
		start_pcv_processing(docname)


def update_default_dimensions(dimension_fields, gl_entry, dimension_values):
	for i, dimension in enumerate(dimension_fields):
		gl_entry[dimension] = dimension_values[i]


def get_gle_for_pl_account(pcv, acc, balances, dimensions):
	balance_in_account_currency = flt(balances.debit_in_account_currency) - flt(
		balances.credit_in_account_currency
	)
	balance_in_company_currency = flt(balances.debit) - flt(balances.credit)
	gl_entry = frappe._dict(
		{
			"company": pcv.company,
			"posting_date": pcv.period_end_date,
			"account": acc,
			"account_currency": balances.account_currency,
			"debit_in_account_currency": abs(balance_in_account_currency)
			if balance_in_account_currency < 0
			else 0,
			"debit": abs(balance_in_company_currency) if balance_in_company_currency < 0 else 0,
			"credit_in_account_currency": abs(balance_in_account_currency)
			if balance_in_account_currency > 0
			else 0,
			"credit": abs(balance_in_company_currency) if balance_in_company_currency > 0 else 0,
			"is_period_closing_voucher_entry": 1,
			"voucher_type": "Period Closing Voucher",
			"voucher_no": pcv.name,
			"fiscal_year": pcv.fiscal_year,
			"remarks": pcv.remarks,
			"is_opening": "No",
		}
	)
	# update dimensions
	update_default_dimensions(get_dimensions(), gl_entry, dimensions)
	return gl_entry


def get_gle_for_closing_account(pcv, dimension_balance, dimensions):
	balance_in_company_currency = flt(dimension_balance.balance_in_company_currency)
	debit = balance_in_company_currency if balance_in_company_currency > 0 else 0
	credit = abs(balance_in_company_currency) if balance_in_company_currency < 0 else 0

	gl_entry = frappe._dict(
		{
			"company": pcv.company,
			"posting_date": pcv.period_end_date,
			"account": pcv.closing_account_head,
			"account_currency": frappe.db.get_value("Account", pcv.closing_account_head, "account_currency"),
			"debit_in_account_currency": debit,
			"debit": debit,
			"credit_in_account_currency": credit,
			"credit": credit,
			"is_period_closing_voucher_entry": 1,
			"voucher_type": "Period Closing Voucher",
			"voucher_no": pcv.name,
			"fiscal_year": pcv.fiscal_year,
			"remarks": pcv.remarks,
			"is_opening": "No",
		}
	)
	# update dimensions
	update_default_dimensions(get_dimensions(), gl_entry, dimensions)
	return gl_entry


@frappe.whitelist()
def schedule_next_date(docname: str):
	if to_process := frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Queued"},
		fields=["processing_date", "report_type", "parentfield"],
		order_by="parentfield, idx, processing_date",
		limit=1,
	):
		if not is_scheduler_inactive():
			frappe.db.set_value(
				"Process Period Closing Voucher Detail",
				{
					"processing_date": to_process[0].processing_date,
					"parent": docname,
					"report_type": to_process[0].report_type,
					"parentfield": to_process[0].parentfield,
				},
				"status",
				"Running",
			)
			frappe.enqueue(
				method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
				queue="long",
				timeout="3600",
				is_async=True,
				enqueue_after_commit=True,
				docname=docname,
				date=to_process[0].processing_date,
				report_type=to_process[0].report_type,
				parentfield=to_process[0].parentfield,
			)
	else:
		ppcvd = qb.DocType("Process Period Closing Voucher Detail")
		total_no_of_dates = (
			qb.from_(ppcvd).select(Count(ppcvd.star)).where(ppcvd.parent.eq(docname)).run()[0][0]
		)
		completed = (
			qb.from_(ppcvd)
			.select(Count(ppcvd.star))
			.where(ppcvd.parent.eq(docname) & ppcvd.status.eq("Completed"))
			.run()[0][0]
		)
		# Ensure both normal and opening balances are processed for all dates
		if total_no_of_dates == completed:
			summarize_and_post_ledger_entries(docname)


def make_dict_json_compliant(dimension_wise_balance) -> dict:
	"""
	convert tuple -> str
	JSON doesn't support dictionary with tuple keys
	"""
	converted_dict = {}
	for k, v in dimension_wise_balance.items():
		str_key = [str(x) for x in k]
		str_key = ",".join(str_key)
		converted_dict[str_key] = v

	return converted_dict


def get_consolidated_gles(balances, report_type) -> list:
	gl_entries = []
	for x in balances:
		if x.report_type == report_type:
			closing_balances = [frappe._dict(gle) for gle in frappe.json.loads(x.closing_balance)]
			gl_entries.extend(closing_balances)
	return gl_entries


def get_gl_entries(docname):
	"""
	Calculate total closing balance of all P&L accounts across PCV start and end date
	"""
	ppcv = frappe.get_doc("Process Period Closing Voucher", docname)

	# calculate balance
	gl_entries = get_consolidated_gles(ppcv.normal_balances, "Profit and Loss")
	pl_dimension_wise_acc_balance = build_dimension_wise_balance_dict(gl_entries)

	# save
	json_dict = make_dict_json_compliant(pl_dimension_wise_acc_balance)
	frappe.db.set_value(
		"Process Period Closing Voucher", docname, "p_l_closing_balance", frappe.json.dumps(json_dict)
	)

	# build gl map
	pcv = frappe.get_doc("Period Closing Voucher", ppcv.parent_pcv)
	pl_accounts_reverse_gle = []
	closing_account_gle = []

	for dimensions, account_balances in pl_dimension_wise_acc_balance.items():
		for acc, balances in account_balances.items():
			balance_in_company_currency = flt(balances.debit) - flt(balances.credit)
			if balance_in_company_currency:
				pl_accounts_reverse_gle.append(get_gle_for_pl_account(pcv, acc, balances, dimensions))

		closing_account_gle.append(get_gle_for_closing_account(pcv, account_balances["balances"], dimensions))

	return pl_accounts_reverse_gle, closing_account_gle


def calculate_balance_sheet_balance(docname):
	"""
	Calculate total closing balance of all P&L accounts across PCV start and end date.
	If it is first PCV, opening entries are also considered
	"""
	ppcv = frappe.get_doc("Process Period Closing Voucher", docname)
	gl_entries = get_consolidated_gles(ppcv.normal_balances + ppcv.z_opening_balances, "Balance Sheet")

	# build dimension wise dictionary from all GLE's
	bs_dimension_wise_acc_balance = build_dimension_wise_balance_dict(gl_entries)

	# save
	json_dict = make_dict_json_compliant(bs_dimension_wise_acc_balance)
	frappe.db.set_value(
		"Process Period Closing Voucher", docname, "bs_closing_balance", frappe.json.dumps(json_dict)
	)
	return bs_dimension_wise_acc_balance


def get_p_l_closing_entries(pl_gles, pcv):
	pl_closing_entries = copy.deepcopy(pl_gles)
	for d in pl_gles:
		# reverse debit and credit
		gle_copy = copy.deepcopy(d)
		gle_copy.debit = d.credit
		gle_copy.credit = d.debit
		gle_copy.debit_in_account_currency = d.credit_in_account_currency
		gle_copy.credit_in_account_currency = d.debit_in_account_currency
		gle_copy.is_period_closing_voucher_entry = 0
		gle_copy.period_closing_voucher = pcv.name
		pl_closing_entries.append(gle_copy)

	return pl_closing_entries


def get_bs_closing_entries(dimension_wise_balance, pcv):
	closing_entries = []
	for dimensions, account_balances in dimension_wise_balance.items():
		for acc, balances in account_balances.items():
			balance_in_company_currency = flt(balances.debit) - flt(balances.credit)
			if acc != "balances" and balance_in_company_currency:
				closing_entries.append(get_closing_entry(pcv, acc, balances, dimensions))

	return closing_entries


def get_closing_account_closing_entry(closing_account_gle, pcv):
	closing_entries_for_closing_account = copy.deepcopy(closing_account_gle)
	for d in closing_entries_for_closing_account:
		d.period_closing_voucher = pcv.name
	return closing_entries_for_closing_account


def summarize_and_post_ledger_entries(docname):
	# P&L accounts
	pl_accounts_reverse_gle, closing_account_gle = get_gl_entries(docname)
	gl_entries = pl_accounts_reverse_gle + closing_account_gle
	from erpnext.accounts.general_ledger import make_gl_entries

	if gl_entries:
		make_gl_entries(gl_entries, merge_entries=False)

	pcv_name = frappe.db.get_value("Process Period Closing Voucher", docname, "parent_pcv")
	pcv = frappe.get_doc("Period Closing Voucher", pcv_name)

	# Balance sheet accounts
	bs_dimension_wise_acc_balance = calculate_balance_sheet_balance(docname)

	pl_closing_entries = get_p_l_closing_entries(pl_accounts_reverse_gle, pcv)
	bs_closing_entries = get_bs_closing_entries(bs_dimension_wise_acc_balance, pcv)
	closing_entries_for_closing_account = get_closing_account_closing_entry(closing_account_gle, pcv)
	closing_entries = pl_closing_entries + bs_closing_entries + closing_entries_for_closing_account

	make_closing_entries(closing_entries, pcv.name, pcv.company, pcv.period_end_date)

	frappe.db.set_value("Period Closing Voucher", pcv.name, "gle_processing_status", "Completed")
	frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


def get_closing_entry(pcv, account, balances, dimensions):
	closing_entry = frappe._dict(
		{
			"company": pcv.company,
			"closing_date": pcv.period_end_date,
			"period_closing_voucher": pcv.name,
			"account": account,
			"account_currency": balances.account_currency,
			"debit_in_account_currency": flt(balances.debit_in_account_currency),
			"debit": flt(balances.debit),
			"credit_in_account_currency": flt(balances.credit_in_account_currency),
			"credit": flt(balances.credit),
			"is_period_closing_voucher_entry": 0,
		}
	)
	# update dimensions
	update_default_dimensions(get_dimensions(), closing_entry, dimensions)
	return closing_entry


def get_dimensions():
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		get_accounting_dimensions,
	)

	default_dimensions = ["cost_center", "finance_book", "project"]
	dimensions = default_dimensions + get_accounting_dimensions()
	return dimensions


def get_dimension_key(res):
	return tuple([res.get(dimension) for dimension in get_dimensions()])


def build_dimension_wise_balance_dict(gl_entries):
	dimension_balances = frappe._dict()
	for x in gl_entries:
		dimension_key = get_dimension_key(x)
		dimension_balances.setdefault(dimension_key, frappe._dict()).setdefault(
			x.account,
			frappe._dict(
				{
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 0,
					"debit": 0,
					"credit": 0,
					"account_currency": x.account_currency,
				}
			),
		)
		dimension_balances[dimension_key][x.account].debit_in_account_currency += flt(
			x.debit_in_account_currency
		)
		dimension_balances[dimension_key][x.account].credit_in_account_currency += flt(
			x.credit_in_account_currency
		)
		dimension_balances[dimension_key][x.account].debit += flt(x.debit)
		dimension_balances[dimension_key][x.account].credit += flt(x.credit)

		# dimension-wise total balances
		dimension_balances[dimension_key].setdefault(
			"balances",
			frappe._dict(
				{
					"balance_in_account_currency": 0,
					"balance_in_company_currency": 0,
				}
			),
		)
		balance_in_account_currency = flt(x.debit_in_account_currency) - flt(x.credit_in_account_currency)
		balance_in_company_currency = flt(x.debit) - flt(x.credit)
		dimension_balances[dimension_key][
			"balances"
		].balance_in_account_currency += balance_in_account_currency
		dimension_balances[dimension_key][
			"balances"
		].balance_in_company_currency += balance_in_company_currency

	return dimension_balances


def process_individual_date(docname: str, date, report_type, parentfield):
	current_date_status = frappe.db.get_value(
		"Process Period Closing Voucher Detail",
		{"processing_date": date, "report_type": report_type, "parentfield": parentfield},
		"status",
	)
	if current_date_status != "Running":
		return

	pcv_name = frappe.db.get_value("Process Period Closing Voucher", docname, "parent_pcv")
	company = frappe.db.get_value("Period Closing Voucher", pcv_name, "company")

	dimensions = get_dimensions()

	accounts = frappe.db.get_all(
		"Account", filters={"company": company, "report_type": report_type}, pluck="name"
	)

	# summarize
	gle = qb.DocType("GL Entry")
	query = qb.from_(gle).select(gle.account)
	for dim in dimensions:
		query = query.select(gle[dim])
	query = query.select(
		Sum(gle.debit).as_("debit"),
		Sum(gle.credit).as_("credit"),
		Sum(gle.debit_in_account_currency).as_("debit_in_account_currency"),
		Sum(gle.credit_in_account_currency).as_("credit_in_account_currency"),
		gle.account_currency,
	).where(
		(gle.company.eq(company))
		& (gle.is_cancelled.eq(0))
		& (gle.posting_date.eq(date))
		& (gle.account.isin(accounts))
	)

	if parentfield == "z_opening_balances":
		query = query.where(gle.is_opening.eq("Yes"))

	query = query.groupby(gle.account)
	for dim in dimensions:
		query = query.groupby(gle[dim])
	res = query.run(as_dict=True)

	# save results
	frappe.db.set_value(
		"Process Period Closing Voucher Detail",
		{"processing_date": date, "parent": docname, "report_type": report_type, "parentfield": parentfield},
		"closing_balance",
		frappe.json.dumps(res),
	)

	frappe.db.set_value(
		"Process Period Closing Voucher Detail",
		{"processing_date": date, "parent": docname, "report_type": report_type, "parentfield": parentfield},
		"status",
		"Completed",
	)

	# chain call
	schedule_next_date(docname)
