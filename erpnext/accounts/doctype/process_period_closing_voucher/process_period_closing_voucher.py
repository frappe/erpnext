# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import qb
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, get_datetime
from frappe.utils.scheduler import is_scheduler_inactive

BACKGROUND = False


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
		dates_to_process: DF.Table[ProcessPeriodClosingVoucherDetail]
		parent_pcv: DF.Link
		status: DF.Literal["Queued", "Running", "Completed"]
		total: DF.JSON | None
	# end: auto-generated types

	def validate(self):
		self.status = "Queued"
		self.populate_processing_table()

	def populate_processing_table(self):
		self.dates_to_process = []
		pcv = frappe.get_doc("Period Closing Voucher", self.parent_pcv)
		start = get_datetime(pcv.period_start_date)
		end = get_datetime(pcv.period_end_date)
		dates = [start + timedelta(days=x) for x in range((end - start).days + 1)]
		for x in dates:
			self.append("dates_to_process", {"processing_date": x, "status": "Queued"})


@frappe.whitelist()
def start_pcv_processing(docname: str):
	if frappe.db.get_value("Process Period Closing Voucher", docname, "status") in ["Queued", "Paused"]:
		frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Running")
		if dates_to_process := frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": docname, "status": "Queued"},
			fields=["processing_date"],
			order_by="processing_date",
			limit=4,
		):
			if not is_scheduler_inactive():
				for x in dates_to_process:
					if BACKGROUND:
						frappe.enqueue(
							method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
							queue="long",
							is_async=True,
							enqueue_after_commit=True,
							docname=docname,
							date=x.processing_date,
						)
					else:
						process_individual_date(docname, x.processing_date)
		else:
			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


@frappe.whitelist()
def pause_pcv_processing(docname: str):
	ppcv = qb.DocType("Process Period Closing Voucher")
	qb.update(ppcv).set(ppcv.status, "Paused").where(ppcv.name.eq(docname)).run()

	queued_dates = frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Queued"},
		pluck="name",
	)
	ppcvd = qb.DocType("Process Period Closing Voucher Detail")
	qb.update(ppcvd).set(ppcvd.status, "Paused").where(ppcvd.name.isin(queued_dates)).run()


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
	for i, dimension in enumerate(dimensions):
		gl_entry[dimension] = dimensions[i]
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
	for i, dimension in enumerate(dimensions):
		gl_entry[dimension] = dimensions[i]
	return gl_entry


@frappe.whitelist()
def call_next_date(docname: str):
	if next_date_to_process := frappe.db.get_all(
		"Process Period Closing Voucher Detail",
		filters={"parent": docname, "status": "Queued"},
		fields=["processing_date"],
		order_by="processing_date",
		limit=1,
	):
		next_date_to_process = next_date_to_process[0].processing_date
		if not is_scheduler_inactive():
			frappe.db.set_value(
				"Process Period Closing Voucher Detail",
				{"processing_date": next_date_to_process, "parent": docname},
				"status",
				"Running",
			)
			if BACKGROUND:
				frappe.enqueue(
					method="erpnext.accounts.doctype.process_period_closing_voucher.process_period_closing_voucher.process_individual_date",
					queue="long",
					is_async=True,
					enqueue_after_commit=True,
					docname=docname,
					date=next_date_to_process,
				)
			else:
				process_individual_date(docname, next_date_to_process)
	else:
		running = frappe.db.get_all(
			"Process Period Closing Voucher Detail",
			filters={"parent": docname, "status": "Running"},
			fields=["processing_date"],
			order_by="processing_date",
			limit=1,
		)
		# TODO: ensure all dates are processed
		if not running:
			# Calculate total balances for PCV period
			# Build dictionary back
			dimension_wise_acc_balances = {}
			ppcv = frappe.get_doc("Process Period Closing Voucher", docname)
			for x in [x.closing_balance for x in ppcv.dates_to_process]:
				bal = frappe.json.loads(x)
				for dimensions, account_balances in bal.items():
					dim_key = tuple([None if x == "None" else x for x in dimensions.split(",")])
					obj = dimension_wise_acc_balances.setdefault(dim_key, frappe._dict())

					for acc, bal in account_balances.items():
						if acc != "balances":
							bal_dict = obj.setdefault(
								acc,
								frappe._dict(
									{
										"debit_in_account_currency": 0,
										"credit_in_account_currency": 0,
										"debit": 0,
										"credit": 0,
										"account_currency": bal["account_currency"],
									}
								),
							)
							bal_dict["debit_in_account_currency"] += bal["debit_in_account_currency"]
							bal_dict["credit_in_account_currency"] += bal["credit_in_account_currency"]
							bal_dict["debit"] += bal["debit"]
							bal_dict["credit"] += bal["credit"]
						else:
							bal_dict = obj.setdefault(
								"balances",
								frappe._dict(
									{
										"balance_in_company_currency": 0,
										"balance_in_account_currency": 0,
									}
								),
							)
							bal_dict["balance_in_company_currency"] += bal["balance_in_company_currency"]
							bal_dict["balance_in_account_currency"] += bal["balance_in_account_currency"]

			# convert dict keys to json compliant json dictionary keys
			json_dict = {}
			for k, v in dimension_wise_acc_balances.items():
				str_key = [str(x) for x in k]
				str_key = ",".join(str_key)
				json_dict[str_key] = v

			frappe.db.set_value(
				"Process Period Closing Voucher", docname, "total", frappe.json.dumps(json_dict)
			)

			# Build GL map
			pcv = frappe.get_doc("Period Closing Voucher", ppcv.parent_pcv)
			pl_accounts_reverse_gle = []
			closing_account_gle = []

			for dimensions, account_balances in dimension_wise_acc_balances.items():
				for acc, balances in account_balances.items():
					balance_in_company_currency = flt(balances.debit) - flt(balances.credit)
					if balance_in_company_currency:
						pl_accounts_reverse_gle.append(get_gle_for_pl_account(pcv, acc, balances, dimensions))

				# closing liability account
				closing_account_gle.append(
					get_gle_for_closing_account(pcv, account_balances["balances"], dimensions)
				)

			gl_entries = pl_accounts_reverse_gle + closing_account_gle
			from erpnext.accounts.general_ledger import make_gl_entries

			if gl_entries:
				make_gl_entries(gl_entries, merge_entries=False)

			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


def get_dimensions():
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		get_accounting_dimensions,
	)

	default_dimensions = ["cost_center", "finance_book", "project"]
	dimensions = default_dimensions + get_accounting_dimensions()
	return dimensions


def get_dimension_key(res):
	return tuple([res.get(dimension) for dimension in get_dimensions()])


def process_individual_date(docname: str, date: str):
	if frappe.db.get_value("Process Period Closing Voucher", docname, "status") == "Running":
		pcv_name = frappe.db.get_value("Process Period Closing Voucher", docname, "parent_pcv")
		pcv = frappe.get_doc("Period Closing Voucher", pcv_name)

		dimensions = get_dimensions()

		p_l_accounts = frappe.db.get_all(
			"Account", filters={"company": pcv.company, "report_type": "Profit and Loss"}, pluck="name"
		)

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
			(gle.company.eq(pcv.company))
			& (gle.is_cancelled.eq(0))
			& (gle.posting_date.eq(date))
			& (gle.account.isin(p_l_accounts))
		)

		query = query.groupby(gle.account)
		for dim in dimensions:
			query = query.groupby(gle[dim])

		res = query.run(as_dict=True)

		dimension_wise_acc_balances = frappe._dict()
		for x in res:
			dimension_key = get_dimension_key(x)
			dimension_wise_acc_balances.setdefault(dimension_key, frappe._dict()).setdefault(
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
			dimension_wise_acc_balances[dimension_key][x.account].debit_in_account_currency += flt(
				x.debit_in_account_currency
			)
			dimension_wise_acc_balances[dimension_key][x.account].credit_in_account_currency += flt(
				x.credit_in_account_currency
			)
			dimension_wise_acc_balances[dimension_key][x.account].debit += flt(x.debit)
			dimension_wise_acc_balances[dimension_key][x.account].credit += flt(x.credit)

			# dimension-wise total balances
			dimension_wise_acc_balances[dimension_key].setdefault(
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

			dimension_wise_acc_balances[dimension_key][
				"balances"
			].balance_in_account_currency += balance_in_account_currency
			dimension_wise_acc_balances[dimension_key][
				"balances"
			].balance_in_company_currency += balance_in_company_currency

		frappe.db.set_value(
			"Process Period Closing Voucher Detail",
			{"processing_date": date, "parent": docname},
			"status",
			"Completed",
		)

		# convert dict keys to json compliant json dictionary keys
		json_dict = {}
		for k, v in dimension_wise_acc_balances.items():
			str_key = [str(x) for x in k]
			str_key = ",".join(str_key)
			json_dict[str_key] = v

		frappe.db.set_value(
			"Process Period Closing Voucher Detail",
			{"processing_date": date, "parent": docname},
			"closing_balance",
			frappe.json.dumps(json_dict),
		)

		call_next_date(docname)
