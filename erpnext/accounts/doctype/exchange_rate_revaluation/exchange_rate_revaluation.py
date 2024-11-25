# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.query_builder import Criterion, Order
from frappe.query_builder.functions import NullIf, Sum
from frappe.utils import flt, get_link_to_form

import erpnext
from erpnext.accounts.doctype.journal_entry.journal_entry import get_balance_on
from erpnext.accounts.utils import get_currency_precision
from erpnext.setup.utils import get_exchange_rate


class ExchangeRateRevaluation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.exchange_rate_revaluation_account.exchange_rate_revaluation_account import (
			ExchangeRateRevaluationAccount,
		)

		accounts: DF.Table[ExchangeRateRevaluationAccount]
		amended_from: DF.Link | None
		company: DF.Link
		gain_loss_booked: DF.Currency
		gain_loss_unbooked: DF.Currency
		posting_date: DF.Date
		rounding_loss_allowance: DF.Float
		total_gain_loss: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_rounding_loss_allowance()
		self.set_total_gain_loss()

	def validate_rounding_loss_allowance(self):
		if not (self.rounding_loss_allowance >= 0 and self.rounding_loss_allowance < 1):
			frappe.throw(_("Rounding Loss Allowance should be between 0 and 1"))

	def set_total_gain_loss(self):
		total_gain_loss = 0

		gain_loss_booked = 0
		gain_loss_unbooked = 0

		for d in self.accounts:
			if not d.zero_balance:
				d.gain_loss = flt(
					d.new_balance_in_base_currency, d.precision("new_balance_in_base_currency")
				) - flt(d.balance_in_base_currency, d.precision("balance_in_base_currency"))

			if d.zero_balance:
				gain_loss_booked += flt(d.gain_loss, d.precision("gain_loss"))
			else:
				gain_loss_unbooked += flt(d.gain_loss, d.precision("gain_loss"))

			total_gain_loss += flt(d.gain_loss, d.precision("gain_loss"))

		self.gain_loss_booked = gain_loss_booked
		self.gain_loss_unbooked = gain_loss_unbooked
		self.total_gain_loss = flt(total_gain_loss, self.precision("total_gain_loss"))

	def validate_mandatory(self):
		if not (self.company and self.posting_date):
			frappe.throw(_("Please select Company and Posting Date to getting entries"))

	def before_submit(self):
		self.remove_accounts_without_gain_loss()

	def remove_accounts_without_gain_loss(self):
		self.accounts = [account for account in self.accounts if account.gain_loss]

		if not self.accounts:
			frappe.throw(_("At least one account with exchange gain or loss is required"))

		frappe.msgprint(
			_("Removing rows without exchange gain or loss"),
			alert=True,
			indicator="yellow",
		)

	def on_cancel(self):
		self.ignore_linked_doctypes = "GL Entry"

	@frappe.whitelist()
	def check_journal_entry_condition(self):
		exchange_gain_loss_account = self.get_for_unrealized_gain_loss_account()

		jea = qb.DocType("Journal Entry Account")
		journals = (
			qb.from_(jea)
			.select(jea.parent)
			.distinct()
			.where(
				(jea.reference_type == "Exchange Rate Revaluation")
				& (jea.reference_name == self.name)
				& (jea.docstatus == 1)
			)
			.run()
		)

		if journals:
			gle = qb.DocType("GL Entry")
			total_amt = (
				qb.from_(gle)
				.select((Sum(gle.credit) - Sum(gle.debit)).as_("total_amount"))
				.where(
					(gle.voucher_type == "Journal Entry")
					& (gle.voucher_no.isin(journals))
					& (gle.account == exchange_gain_loss_account)
					& (gle.is_cancelled == 0)
				)
				.run()
			)

			if total_amt and total_amt[0][0] != self.total_gain_loss:
				return True
			else:
				return False

		return True

	def fetch_and_calculate_accounts_data(self):
		accounts = self.get_accounts_data()
		if accounts:
			for acc in accounts:
				self.append("accounts", acc)

	@frappe.whitelist()
	def get_accounts_data(self):
		self.validate_mandatory()
		account_details = self.get_account_balance_from_gle(
			company=self.company,
			posting_date=self.posting_date,
			account=None,
			party_type=None,
			party=None,
			rounding_loss_allowance=self.rounding_loss_allowance,
		)
		accounts_with_new_balance = self.calculate_new_account_balance(
			self.company, self.posting_date, account_details
		)

		if not accounts_with_new_balance:
			self.throw_invalid_response_message(account_details)

		return accounts_with_new_balance

	@staticmethod
	def get_account_balance_from_gle(
		company, posting_date, account, party_type, party, rounding_loss_allowance
	):
		account_details = []

		if company and posting_date:
			company_currency = erpnext.get_company_currency(company)

			acc = qb.DocType("Account")
			if account:
				accounts = [account]
			else:
				res = (
					qb.from_(acc)
					.select(acc.name)
					.where(
						(acc.is_group == 0)
						& (acc.report_type == "Balance Sheet")
						& (acc.root_type.isin(["Asset", "Liability", "Equity"]))
						& (acc.account_type != "Stock")
						& (acc.company == company)
						& (acc.account_currency != company_currency)
					)
					.orderby(acc.name)
					.run(as_list=True)
				)
				accounts = [x[0] for x in res]

			if accounts:
				having_clause = (qb.Field("balance") != qb.Field("balance_in_account_currency")) & (
					(qb.Field("balance_in_account_currency") != 0) | (qb.Field("balance") != 0)
				)

				gle = qb.DocType("GL Entry")

				# conditions
				conditions = []
				conditions.append(gle.account.isin(accounts))
				conditions.append(gle.posting_date.lte(posting_date))
				conditions.append(gle.is_cancelled == 0)

				if party_type:
					conditions.append(gle.party_type == party_type)
				if party:
					conditions.append(gle.party == party)

				account_details = (
					qb.from_(gle)
					.select(
						gle.account,
						gle.party_type,
						gle.party,
						gle.account_currency,
						(Sum(gle.debit_in_account_currency) - Sum(gle.credit_in_account_currency)).as_(
							"balance_in_account_currency"
						),
						(Sum(gle.debit) - Sum(gle.credit)).as_("balance"),
						(Sum(gle.debit) - Sum(gle.credit) == 0)
						^ (Sum(gle.debit_in_account_currency) - Sum(gle.credit_in_account_currency) == 0).as_(
							"zero_balance"
						),
					)
					.where(Criterion.all(conditions))
					.groupby(gle.account, NullIf(gle.party_type, ""), NullIf(gle.party, ""))
					.having(having_clause)
					.orderby(gle.account)
					.run(as_dict=True)
				)

				# round off balance based on currency precision
				# and consider debit-credit difference allowance
				currency_precision = get_currency_precision()
				rounding_loss_allowance = float(rounding_loss_allowance)
				for acc in account_details:
					acc.balance_in_account_currency = flt(acc.balance_in_account_currency, currency_precision)
					if abs(acc.balance_in_account_currency) <= rounding_loss_allowance:
						acc.balance_in_account_currency = 0

					acc.balance = flt(acc.balance, currency_precision)
					if abs(acc.balance) <= rounding_loss_allowance:
						acc.balance = 0

					acc.zero_balance = (
						True if (acc.balance == 0 or acc.balance_in_account_currency == 0) else False
					)

		return account_details

	@staticmethod
	def calculate_new_account_balance(company, posting_date, account_details):
		accounts = []
		company_currency = erpnext.get_company_currency(company)
		precision = get_field_precision(
			frappe.get_meta("Exchange Rate Revaluation Account").get_field("new_balance_in_base_currency"),
			company_currency,
		)

		if account_details:
			# Handle Accounts with balance in both Account/Base Currency
			for d in [x for x in account_details if not x.zero_balance]:
				current_exchange_rate = (
					d.balance / d.balance_in_account_currency if d.balance_in_account_currency else 0
				)
				new_exchange_rate = get_exchange_rate(d.account_currency, company_currency, posting_date)
				new_balance_in_base_currency = flt(d.balance_in_account_currency * new_exchange_rate)
				gain_loss = flt(new_balance_in_base_currency, precision) - flt(d.balance, precision)

				accounts.append(
					{
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"account_currency": d.account_currency,
						"balance_in_base_currency": d.balance,
						"balance_in_account_currency": d.balance_in_account_currency,
						"zero_balance": d.zero_balance,
						"current_exchange_rate": current_exchange_rate,
						"new_exchange_rate": new_exchange_rate,
						"new_balance_in_base_currency": new_balance_in_base_currency,
						"new_balance_in_account_currency": d.balance_in_account_currency,
						"gain_loss": gain_loss,
					}
				)

			# Handle Accounts with '0' balance in Account/Base Currency
			for d in [x for x in account_details if x.zero_balance]:
				if d.balance != 0:
					current_exchange_rate = new_exchange_rate = 0

					new_balance_in_account_currency = 0  # this will be '0'
					new_balance_in_base_currency = 0  # this will be '0'
					gain_loss = flt(new_balance_in_base_currency, precision) - flt(d.balance, precision)
				else:
					new_exchange_rate = 0
					new_balance_in_base_currency = 0
					new_balance_in_account_currency = 0

					current_exchange_rate = (
						calculate_exchange_rate_using_last_gle(company, d.account, d.party_type, d.party)
						or 0.0
					)

					gain_loss = new_balance_in_account_currency - (
						current_exchange_rate * d.balance_in_account_currency
					)

				accounts.append(
					{
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"account_currency": d.account_currency,
						"balance_in_base_currency": d.balance,
						"balance_in_account_currency": d.balance_in_account_currency,
						"zero_balance": d.zero_balance,
						"current_exchange_rate": current_exchange_rate,
						"new_exchange_rate": new_exchange_rate,
						"new_balance_in_base_currency": new_balance_in_base_currency,
						"new_balance_in_account_currency": new_balance_in_account_currency,
						"gain_loss": gain_loss,
					}
				)

		return accounts

	def throw_invalid_response_message(self, account_details):
		if account_details:
			message = _("No outstanding invoices require exchange rate revaluation")
		else:
			message = _("No outstanding invoices found")
		frappe.msgprint(message)

	def get_for_unrealized_gain_loss_account(self):
		unrealized_exchange_gain_loss_account = frappe.get_cached_value(
			"Company", self.company, "unrealized_exchange_gain_loss_account"
		)
		if not unrealized_exchange_gain_loss_account:
			frappe.throw(
				_("Please set Unrealized Exchange Gain/Loss Account in Company {0}").format(self.company)
			)
		return unrealized_exchange_gain_loss_account

	@frappe.whitelist()
	def make_jv_entries(self):
		zero_balance_jv = self.make_jv_for_zero_balance()
		if zero_balance_jv:
			frappe.msgprint(
				f"Zero Balance Journal: {get_link_to_form('Journal Entry', zero_balance_jv.name)}"
			)

		revaluation_jv = self.make_jv_for_revaluation()
		if revaluation_jv:
			frappe.msgprint(f"Revaluation Journal: {get_link_to_form('Journal Entry', revaluation_jv.name)}")

		return {
			"revaluation_jv": revaluation_jv.name if revaluation_jv else None,
			"zero_balance_jv": zero_balance_jv.name if zero_balance_jv else None,
		}

	def make_jv_for_zero_balance(self):
		if self.gain_loss_booked == 0:
			return

		accounts = [x for x in self.accounts if x.zero_balance]

		if not accounts:
			return

		unrealized_exchange_gain_loss_account = self.get_for_unrealized_gain_loss_account()

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Exchange Gain Or Loss"
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.multi_currency = 1

		journal_entry_accounts = []
		for d in accounts:
			journal_account = frappe._dict(
				{
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"balance": flt(
						d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")
					),
					"exchange_rate": 0,
					"cost_center": erpnext.get_default_cost_center(self.company),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				}
			)

			# Account Currency has balance
			if d.get("balance_in_account_currency") and not d.get("new_balance_in_account_currency"):
				dr_or_cr = (
					"credit_in_account_currency"
					if d.get("balance_in_account_currency") > 0
					else "debit_in_account_currency"
				)
				reverse_dr_or_cr = (
					"debit_in_account_currency"
					if dr_or_cr == "credit_in_account_currency"
					else "credit_in_account_currency"
				)
				journal_account.update(
					{
						dr_or_cr: flt(
							abs(d.get("balance_in_account_currency")),
							d.precision("balance_in_account_currency"),
						),
						reverse_dr_or_cr: 0,
						"debit": 0,
						"credit": 0,
					}
				)

				journal_entry_accounts.append(journal_account)

				journal_entry_accounts.append(
					{
						"account": unrealized_exchange_gain_loss_account,
						"balance": get_balance_on(unrealized_exchange_gain_loss_account),
						"debit": 0,
						"credit": 0,
						"debit_in_account_currency": abs(d.gain_loss) if d.gain_loss < 0 else 0,
						"credit_in_account_currency": abs(d.gain_loss) if d.gain_loss > 0 else 0,
						"cost_center": erpnext.get_default_cost_center(self.company),
						"exchange_rate": 1,
						"reference_type": "Exchange Rate Revaluation",
						"reference_name": self.name,
					}
				)

			elif d.get("balance_in_base_currency") and not d.get("new_balance_in_base_currency"):
				# Base currency has balance
				dr_or_cr = "credit" if d.get("balance_in_base_currency") > 0 else "debit"
				reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"
				journal_account.update(
					{
						dr_or_cr: flt(
							abs(d.get("balance_in_base_currency")), d.precision("balance_in_base_currency")
						),
						reverse_dr_or_cr: 0,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": 0,
					}
				)

				journal_entry_accounts.append(journal_account)

				journal_entry_accounts.append(
					{
						"account": unrealized_exchange_gain_loss_account,
						"balance": get_balance_on(unrealized_exchange_gain_loss_account),
						"debit": abs(d.gain_loss) if d.gain_loss < 0 else 0,
						"credit": abs(d.gain_loss) if d.gain_loss > 0 else 0,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": 0,
						"cost_center": erpnext.get_default_cost_center(self.company),
						"exchange_rate": 1,
						"reference_type": "Exchange Rate Revaluation",
						"reference_name": self.name,
					}
				)

		journal_entry.set("accounts", journal_entry_accounts)
		journal_entry.set_total_debit_credit()
		journal_entry.save()
		return journal_entry

	def make_jv_for_revaluation(self):
		if self.gain_loss_unbooked == 0:
			return

		accounts = [x for x in self.accounts if not x.zero_balance]
		if not accounts:
			return

		unrealized_exchange_gain_loss_account = self.get_for_unrealized_gain_loss_account()

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Exchange Rate Revaluation"
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.multi_currency = 1

		journal_entry_accounts = []
		for d in accounts:
			if not flt(d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")):
				continue

			dr_or_cr = (
				"debit_in_account_currency"
				if d.get("balance_in_account_currency") > 0
				else "credit_in_account_currency"
			)

			reverse_dr_or_cr = (
				"debit_in_account_currency"
				if dr_or_cr == "credit_in_account_currency"
				else "credit_in_account_currency"
			)

			journal_entry_accounts.append(
				{
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"balance": flt(
						d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")
					),
					dr_or_cr: flt(
						abs(d.get("balance_in_account_currency")), d.precision("balance_in_account_currency")
					),
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(d.get("new_exchange_rate"), d.precision("new_exchange_rate")),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				}
			)
			journal_entry_accounts.append(
				{
					"account": d.get("account"),
					"party_type": d.get("party_type"),
					"party": d.get("party"),
					"account_currency": d.get("account_currency"),
					"balance": flt(
						d.get("balance_in_account_currency"), d.precision("balance_in_account_currency")
					),
					reverse_dr_or_cr: flt(
						abs(d.get("balance_in_account_currency")), d.precision("balance_in_account_currency")
					),
					"cost_center": erpnext.get_default_cost_center(self.company),
					"exchange_rate": flt(
						d.get("current_exchange_rate"), d.precision("current_exchange_rate")
					),
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": self.name,
				}
			)

		journal_entry.set("accounts", journal_entry_accounts)
		journal_entry.set_amounts_in_company_currency()
		journal_entry.set_total_debit_credit()

		self.gain_loss_unbooked += journal_entry.difference - self.gain_loss_unbooked
		journal_entry.append(
			"accounts",
			{
				"account": unrealized_exchange_gain_loss_account,
				"balance": get_balance_on(unrealized_exchange_gain_loss_account),
				"debit_in_account_currency": abs(self.gain_loss_unbooked)
				if self.gain_loss_unbooked < 0
				else 0,
				"credit_in_account_currency": self.gain_loss_unbooked if self.gain_loss_unbooked > 0 else 0,
				"cost_center": erpnext.get_default_cost_center(self.company),
				"exchange_rate": 1,
				"reference_type": "Exchange Rate Revaluation",
				"reference_name": self.name,
			},
		)

		journal_entry.set_amounts_in_company_currency()
		journal_entry.set_total_debit_credit()
		journal_entry.save()
		return journal_entry


def calculate_exchange_rate_using_last_gle(company, account, party_type, party):
	"""
	Use last GL entry to calculate exchange rate
	"""
	last_exchange_rate = None
	if company and account:
		gl = qb.DocType("GL Entry")

		# build conditions
		conditions = []
		conditions.append(gl.company == company)
		conditions.append(gl.account == account)
		conditions.append(gl.is_cancelled == 0)
		conditions.append((gl.debit > 0) | (gl.credit > 0))
		conditions.append((gl.debit_in_account_currency > 0) | (gl.credit_in_account_currency > 0))
		if party_type:
			conditions.append(gl.party_type == party_type)
		if party:
			conditions.append(gl.party == party)

		voucher_type, voucher_no = (
			qb.from_(gl)
			.select(gl.voucher_type, gl.voucher_no)
			.where(Criterion.all(conditions))
			.orderby(gl.posting_date, order=Order.desc)
			.limit(1)
			.run()[0]
		)

		last_exchange_rate = (
			qb.from_(gl)
			.select((gl.debit - gl.credit) / (gl.debit_in_account_currency - gl.credit_in_account_currency))
			.where(
				(gl.voucher_type == voucher_type) & (gl.voucher_no == voucher_no) & (gl.account == account)
			)
			.orderby(gl.posting_date, order=Order.desc)
			.limit(1)
			.run()[0][0]
		)

	return last_exchange_rate


@frappe.whitelist()
def get_account_details(
	company, posting_date, account, party_type=None, party=None, rounding_loss_allowance: float | None = None
):
	if not (company and posting_date):
		frappe.throw(_("Company and Posting Date is mandatory"))

	account_currency, account_type = frappe.get_cached_value(
		"Account", account, ["account_currency", "account_type"]
	)

	if account_type in ["Receivable", "Payable"] and not (party_type and party):
		frappe.throw(_("Party Type and Party is mandatory for {0} account").format(account_type))

	account_details = {}
	erpnext.get_company_currency(company)

	account_details = {
		"account_currency": account_currency,
	}
	account_balance = ExchangeRateRevaluation.get_account_balance_from_gle(
		company=company,
		posting_date=posting_date,
		account=account,
		party_type=party_type,
		party=party,
		rounding_loss_allowance=rounding_loss_allowance,
	)

	if account_balance and (account_balance[0].balance or account_balance[0].balance_in_account_currency):
		if account_with_new_balance := ExchangeRateRevaluation.calculate_new_account_balance(
			company, posting_date, account_balance
		):
			row = account_with_new_balance[0]
			account_details.update(
				{
					"balance_in_base_currency": row["balance_in_base_currency"],
					"balance_in_account_currency": row["balance_in_account_currency"],
					"current_exchange_rate": row["current_exchange_rate"],
					"new_exchange_rate": row["new_exchange_rate"],
					"new_balance_in_base_currency": row["new_balance_in_base_currency"],
					"new_balance_in_account_currency": row["new_balance_in_account_currency"],
					"zero_balance": row["zero_balance"],
					"gain_loss": row["gain_loss"],
				}
			)

	return account_details
