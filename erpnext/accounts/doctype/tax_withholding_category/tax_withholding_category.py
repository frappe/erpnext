# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import getdate

from erpnext import allow_regional
from erpnext.controllers.accounts_controller import validate_account_head


class TaxWithholdingCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.tax_withholding_account.tax_withholding_account import (
			TaxWithholdingAccount,
		)
		from erpnext.accounts.doctype.tax_withholding_rate.tax_withholding_rate import TaxWithholdingRate

		accounts: DF.Table[TaxWithholdingAccount]
		category_name: DF.Data | None
		disable_cumulative_threshold: DF.Check
		disable_transaction_threshold: DF.Check
		rates: DF.Table[TaxWithholdingRate]
		round_off_tax_amount: DF.Check
		tax_deduction_basis: DF.Literal["", "Gross Total", "Net Total"]
		tax_on_excess_amount: DF.Check
	# end: auto-generated types

	def validate(self):
		# TODO: Disable single threshold if tax on excess is enabled
		self.validate_dates()
		self.validate_companies_and_accounts()
		self.validate_thresholds()

	def validate_dates(self):
		group_rates = defaultdict(list)
		for d in self.get("rates"):
			if getdate(d.from_date) >= getdate(d.to_date):
				frappe.throw(_("Row #{0}: From Date cannot be before To Date").format(d.idx))
			group_rates[d.tax_withholding_group].append(d)

		# Validate overlapping dates within each group
		for group, rates in group_rates.items():
			rates = sorted(rates, key=lambda d: getdate(d.from_date))
			last_to_date = None

			for d in rates:
				if last_to_date and getdate(d.from_date) < getdate(last_to_date):
					frappe.throw(
						_("Row #{0}: Dates overlapping with other row in group {1}").format(
							d.idx, group or "Default"
						)
					)

				last_to_date = d.to_date

	def validate_companies_and_accounts(self):
		existing_accounts = set()
		companies = set()
		for d in self.get("accounts"):
			# validate duplicate company
			if d.get("company") in companies:
				frappe.throw(_("Company {0} added multiple times").format(frappe.bold(d.get("company"))))
			companies.add(d.get("company"))

			# validate duplicate account
			if d.get("account") in existing_accounts:
				frappe.throw(_("Account {0} added multiple times").format(frappe.bold(d.get("account"))))

			validate_account_head(d.idx, d.get("account"), d.get("company"))
			existing_accounts.add(d.get("account"))

	def validate_thresholds(self):
		for d in self.get("rates"):
			if d.cumulative_threshold and d.single_threshold and d.cumulative_threshold < d.single_threshold:
				frappe.throw(
					_(
						"Row #{0}: Cumulative threshold cannot be less than Single Transaction threshold"
					).format(d.idx)
				)

	def get_applicable_tax_row(self, posting_date, tax_withholding_group):
		for row in self.rates:
			if (
				getdate(row.from_date) <= getdate(posting_date) <= getdate(row.to_date)
				and row.tax_withholding_group == tax_withholding_group
			):
				return row

		frappe.throw(_("No Tax Withholding data found for the current posting date."))

	def get_company_account(self, company):
		for row in self.accounts:
			if company == row.company:
				return row.account

		frappe.throw(
			_("No Tax withholding account set for Company {0} in Tax Withholding Category {1}.").format(
				frappe.bold(company), frappe.bold(self.name)
			)
		)


class TaxWithholdingDetails:
	def __init__(
		self,
		tax_withholding_categories: list[str],
		tax_withholding_group: str,
		posting_date: str,
		party_type: str,
		party: str,
		company: str,
	):
		self.tax_withholding_categories = tax_withholding_categories
		self.tax_withholding_group = tax_withholding_group
		self.posting_date = posting_date
		self.party_type = party_type
		self.party = party
		self.company = company

	def get(self) -> list:
		"""
		Fetches tax withholding categories based on the provided parameters.
		"""
		category_details = frappe._dict()
		if not self.tax_withholding_categories:
			return category_details

		ldc_details = self.get_ldc_details()

		for category_name in self.tax_withholding_categories:
			doc: TaxWithholdingCategory = frappe.get_cached_doc("Tax Withholding Category", category_name)
			row = doc.get_applicable_tax_row(self.posting_date, self.tax_withholding_group)
			account_head = doc.get_company_account(self.company)

			category_detail = frappe._dict(
				name=category_name,
				description=doc.category_name,
				account_head=account_head,
				# rates
				tax_rate=row.tax_withholding_rate,
				from_date=row.from_date,
				to_date=row.to_date,
				single_threshold=row.single_threshold,
				cumulative_threshold=row.cumulative_threshold,
				# settings
				tax_deduction_basis=doc.tax_deduction_basis,
				round_off_tax_amount=doc.round_off_tax_amount,
				tax_on_excess_amount=doc.tax_on_excess_amount,
				disable_cumulative_threshold=doc.disable_cumulative_threshold,
				disable_transaction_threshold=doc.disable_transaction_threshold,
				taxable_amount=0,
			)

			# ldc (only if valid based on posting date)
			if ldc_detail := ldc_details.get(category_name):
				category_detail.update(ldc_detail)

			category_details[category_name] = category_detail

		return category_details

	def get_ldc_details(self):
		"""
		Fetches the Lower Deduction Certificate (LDC) details for the given party.
		Assumes that only one LDC per category can be valid at a time.
		"""
		ldc_details = {}

		if self.party_type != "Supplier":
			return ldc_details

		# NOTE: This can be a configurable option
		# To check if filter by tax_id is needed
		tax_id = get_tax_id_for_party(self.party_type, self.party)

		# ldc details
		ldc_records = self.get_valid_ldc_records(tax_id)
		if not ldc_records:
			return ldc_details

		ldc_names = [ldc.name for ldc in ldc_records]
		ldc_utilization_map = self.get_ldc_utilization_by_category(ldc_names, tax_id)

		# map
		for ldc in ldc_records:
			category_name = ldc.tax_withholding_category

			unutilized_amount = ldc.certificate_limit - (ldc_utilization_map.get(ldc.name) or 0)
			if not unutilized_amount:
				continue

			ldc_details[category_name] = dict(
				ldc_certificate=ldc.name,
				ldc_unutilized_amount=unutilized_amount,
				ldc_rate=ldc.rate,
			)

		return ldc_details

	def get_valid_ldc_records(self, tax_id):
		ldc = frappe.qb.DocType("Lower Deduction Certificate")
		query = (
			frappe.qb.from_(ldc)
			.select(
				ldc.name,
				ldc.tax_withholding_category,
				ldc.rate,
				ldc.certificate_limit,
			)
			.where(
				(ldc.valid_from <= self.posting_date)
				& (ldc.valid_upto >= self.posting_date)
				& (ldc.company == self.company)
				& ldc.tax_withholding_category.isin(self.tax_withholding_categories)
			)
		)

		query = query.where(ldc.pan_no == tax_id) if tax_id else query.where(ldc.supplier == self.party)

		return query.run(as_dict=True)

	def get_ldc_utilization_by_category(self, ldc_names, tax_id):
		twe = frappe.qb.DocType("Tax Withholding Entry")
		query = (
			frappe.qb.from_(twe)
			.select(twe.lower_deduction_certificate, Sum(twe.taxable_amount).as_("limit_consumed"))
			.where(
				(twe.company == self.company)
				& (twe.party_type == self.party_type)
				& (twe.tax_withholding_category.isin(self.tax_withholding_categories))
				& (twe.lower_deduction_certificate.isin(ldc_names))
				& (twe.docstatus == 1)
				& (twe.status.isin(["Settled", "Over Withheld"]))
			)
			.groupby(twe.lower_deduction_certificate)
		)

		query = query.where(twe.tax_id == tax_id) if tax_id else query.where(twe.party == self.party)

		return frappe._dict(query.run())


@allow_regional
def get_tax_id_for_party(party_type, party):
	return None
