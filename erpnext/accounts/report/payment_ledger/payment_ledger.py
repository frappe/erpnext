# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion


class PaymentLedger:
	def __init__(self, filters=None):
		self.filters = filters
		self.columns, self.data = [], []
		self.voucher_dict = OrderedDict()
		self.voucher_amount = []
		self.ple = qb.DocType("Payment Ledger Entry")

	def init_voucher_dict(self):
		if self.voucher_amount:
			# for each ple, using group_by_key to create a key and assign it to +/- list
			for ple in self.voucher_amount:
				group_by_key = None
				if not self.filters.group_party:
					group_by_key = (ple.against_voucher_type, ple.against_voucher_no, ple.party)
				else:
					group_by_key = (ple.party_type, ple.party)

				target = None
				if ple.amount > 0:
					target = self.voucher_dict.setdefault(group_by_key, {}).setdefault("increase", [])
				else:
					target = self.voucher_dict.setdefault(group_by_key, {}).setdefault("decrease", [])

				# this if condition will lose unassigned ple entries(against_voucher doc doesn't have ple)
				# need to somehow include the stray entries as well.
				if target is not None:
					entry = frappe._dict(
						posting_date=ple.posting_date,
						account=ple.account,
						party_type=ple.party_type,
						party=ple.party,
						voucher_type=ple.voucher_type,
						voucher_no=ple.voucher_no,
						against_voucher_type=ple.against_voucher_type,
						against_voucher_no=ple.against_voucher_no,
						amount=ple.amount,
						currency=ple.account_currency,
						company=ple.company,
					)

					if self.filters.include_account_currency:
						entry["amount_in_account_currency"] = ple.amount_in_account_currency

					target.append(entry)

	def build_data(self):
		self.data.clear()

		for value in self.voucher_dict.values():
			voucher_data = []
			if value.get("increase"):
				voucher_data.extend(value.get("increase"))
			if value.get("decrease"):
				voucher_data.extend(value.get("decrease"))

			if voucher_data:
				# balance row
				total = 0
				total_in_account_currency = 0

				for x in voucher_data:
					total += x.amount
					if self.filters.include_account_currency:
						total_in_account_currency += x.amount_in_account_currency

				entry = frappe._dict(
					against_voucher_no="Outstanding:",
					amount=total,
					currency=voucher_data[0].currency,
					company=voucher_data[0].company,
				)

				if self.filters.include_account_currency:
					entry["amount_in_account_currency"] = total_in_account_currency

				voucher_data.append(entry)

				# empty row
				voucher_data.append(
					frappe._dict(
						currency=voucher_data[0].currency,
						company=voucher_data[0].company,
					)
				)
				self.data.extend(voucher_data)

	def build_conditions(self):
		self.conditions = []

		if self.filters.company:
			self.conditions.append(self.ple.company == self.filters.company)

		if self.filters.account:
			self.conditions.append(self.ple.account.isin(self.filters.account))

		if self.filters.period_start_date:
			self.conditions.append(self.ple.posting_date.gte(self.filters.period_start_date))

		if self.filters.period_end_date:
			self.conditions.append(self.ple.posting_date.lte(self.filters.period_end_date))

		if self.filters.voucher_no:
			self.conditions.append(self.ple.voucher_no == self.filters.voucher_no)

		if self.filters.against_voucher_no:
			self.conditions.append(self.ple.against_voucher_no == self.filters.against_voucher_no)

		if self.filters.party_type:
			self.conditions.append(self.ple.party_type == self.filters.party_type)

		if self.filters.party:
			self.conditions.append(self.ple.party.isin(self.filters.party))

	def get_data(self):
		ple = self.ple

		self.build_conditions()

		# fetch data from table
		self.voucher_amount = (
			qb.from_(ple)
			.select(ple.star)
			.where(ple.delinked == 0)
			.where(Criterion.all(self.conditions))
			.run(as_dict=True)
		)

	def get_columns(self):
		options = None
		self.columns.append(
			dict(
				label=_("Posting Date"),
				fieldname="posting_date",
				fieldtype="Date",
				options=options,
				width="100",
			)
		)

		self.columns.append(
			dict(label=_("Account"), fieldname="account", fieldtype="data", options=options, width="100")
		)

		self.columns.append(
			dict(
				label=_("Party Type"), fieldname="party_type", fieldtype="data", options=options, width="100"
			)
		)
		self.columns.append(
			dict(label=_("Party"), fieldname="party", fieldtype="data", options=options, width="100")
		)
		self.columns.append(
			dict(
				label=_("Voucher Type"),
				fieldname="voucher_type",
				fieldtype="data",
				options=options,
				width="100",
			)
		)
		self.columns.append(
			dict(
				label=_("Voucher No"),
				fieldname="voucher_no",
				fieldtype="Dynamic Link",
				options="voucher_type",
				width="100",
			)
		)
		self.columns.append(
			dict(
				label=_("Against Voucher Type"),
				fieldname="against_voucher_type",
				fieldtype="data",
				options=options,
				width="100",
			)
		)
		self.columns.append(
			dict(
				label=_("Against Voucher No"),
				fieldname="against_voucher_no",
				fieldtype="Dynamic Link",
				options="against_voucher_type",
				width="100",
			)
		)
		self.columns.append(
			dict(
				label=_("Amount"),
				fieldname="amount",
				fieldtype="Currency",
				options="Company:company:default_currency",
				width="100",
			)
		)

		if self.filters.include_account_currency:
			self.columns.append(
				dict(
					label=_("Amount in Account Currency"),
					fieldname="amount_in_account_currency",
					fieldtype="Currency",
					options="currency",
					width="100",
				)
			)
		self.columns.append(
			dict(label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", hidden=True)
		)

	def run(self):
		self.get_columns()
		self.get_data()

		# initialize dictionary and group using key
		self.init_voucher_dict()

		# convert dictionary to list and add balance rows
		self.build_data()

		return self.columns, self.data


def execute(filters=None):
	return PaymentLedger(filters).run()
