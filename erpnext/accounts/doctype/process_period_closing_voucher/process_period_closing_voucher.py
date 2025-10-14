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
		if not running:
			# TODO: Generate GL and Account Closing Balance
			frappe.db.set_value("Process Period Closing Voucher", docname, "status", "Completed")


def get_dimensions():
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		get_accounting_dimensions,
	)

	default_dimensions = ["cost_center", "finance_book", "project"]
	dimensions = default_dimensions + get_accounting_dimensions()
	return dimensions


def get_key(res):
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
			dimension_key = get_key(x)
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
