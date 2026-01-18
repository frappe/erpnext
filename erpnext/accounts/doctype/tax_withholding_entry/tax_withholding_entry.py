# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict, deque
from math import inf

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt

import erpnext
from erpnext.accounts.utils import get_advance_payment_doctypes

DOCTYPE = "Tax Withholding Entry"


class TaxWithholdingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		conversion_rate: DF.Float
		created_by_migration: DF.Check
		currency: DF.Link | None
		lower_deduction_certificate: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		status: DF.Literal["", "Settled", "Under Withheld", "Over Withheld", "Duplicate", "Cancelled"]
		tax_id: DF.Data | None
		tax_rate: DF.Percent
		tax_withholding_category: DF.Link | None
		tax_withholding_group: DF.Link | None
		taxable_amount: DF.Currency
		taxable_date: DF.Date | None
		taxable_doctype: DF.Link | None
		taxable_name: DF.DynamicLink | None
		under_withheld_reason: DF.Literal["", "Threshold Exemption", "Lower Deduction Certificate"]
		withholding_amount: DF.Currency
		withholding_date: DF.Date | None
		withholding_doctype: DF.Link | None
		withholding_name: DF.DynamicLink | None
	# end: auto-generated types

	def set_status(self, status=None):
		if not status:
			status = self.get_status()

		self.status = status

	def get_status(self):
		if self.docstatus == 2:
			return "Cancelled"

		# Reasons are genuine allowed reasons for under deduction.
		# Hence if a reason is provided, consider it as matched.
		if not self.withholding_name and not self.under_withheld_reason:
			return "Under Withheld"

		elif not self.taxable_name:
			return "Over Withheld"

		else:
			return "Settled"

	def validate_adjustments(self):
		if self.is_taxable_different and self.is_withholding_different:
			frappe.throw(
				_(
					"Row #{0}: Cannot create entry with different taxable AND withholding document links."
				).format(self.idx)
			)

	def validate_tax_withheld_amount(self):
		if not self.withholding_name or self.under_withheld_reason:
			return

		precision = self.precision("withholding_amount")
		allowance = 0.5

		tax_to_withheld = flt(self.taxable_amount * (self.tax_rate / 100), precision)
		diff = abs(tax_to_withheld - self.withholding_amount)
		if diff > allowance:
			frappe.throw(
				_("Row #{0}: Withholding Amount {1} does not match calculated amount {2}.").format(
					self.idx, self.withholding_amount, tax_to_withheld
				)
			)

	@property
	def is_taxable_different(self):
		return self.taxable_doctype != self.parenttype or self.taxable_name != self.parent

	@property
	def is_withholding_different(self):
		return self.withholding_doctype != self.parenttype or self.withholding_name != self.parent

	def _process_tax_withholding_adjustments(self):
		if self.status != "Settled":
			return
		# adjust old taxable (under-withheld)
		if self.is_taxable_different:
			self._adjust_against_old_entries(field_type="taxable")

		# adjust old withholding (over-withheld)
		elif self.is_withholding_different:
			self._adjust_against_old_entries(field_type="withholding")

	def _adjust_against_old_entries(self, field_type: str) -> set:
		"""
		Find old entries that need adjustment and update them.
		The logic reads like: "Match up old incomplete entries with this new entry"

		Args:
		                field_type: Either "taxable" or "withholding" - determines which fields to use
		"""

		doctype_field = f"{field_type}_doctype"
		docname_field = f"{field_type}_name"
		amount_field = f"{field_type}_amount"
		status_to_find = "Under Withheld" if field_type == "taxable" else "Over Withheld"

		if not self.tax_rate:
			amount_field = "taxable_amount"

		# old entries
		old_entries = frappe.get_all(
			DOCTYPE,
			filters={
				# NOTE: Allow offsetting across different categories
				# Change Filters
				"tax_withholding_category": self.tax_withholding_category,
				"status": status_to_find,
				doctype_field: self.get(doctype_field),
				docname_field: self.get(docname_field),
				"docstatus": 1,
			},
			fields="*",
		)

		value_direction = -1 if self.get(amount_field) < 0 else 1
		remaining_amount = abs(self.get(amount_field))
		docs_needing_reindex = set()
		precision = self.precision("taxable_amount")

		# update
		for old_entry_data in old_entries:
			old_entry = frappe.get_doc(DOCTYPE, **old_entry_data)
			old_amount = abs(old_entry.get(amount_field))

			if old_entry.get(amount_field) * value_direction < 0:
				# sign of old entry's amount is different
				continue

			amount_we_can_match = min(old_amount, remaining_amount)
			proportion = amount_we_can_match / old_amount if old_amount else 0
			values_to_update = self._get_values_to_update(old_entry, proportion, field_type)

			if old_amount <= amount_we_can_match:
				# complete adjustment
				frappe.db.set_value(DOCTYPE, old_entry.name, values_to_update)

			else:
				# partial adjustment
				# Calculate balance values for both taxable and withholding amounts
				balance_amount = (old_amount - amount_we_can_match) * value_direction

				balance_values = self._get_balance_values_to_update(old_entry, proportion, field_type)
				balance_values[amount_field] = balance_amount

				frappe.db.set_value(DOCTYPE, old_entry.name, balance_values)

				# new entry
				# For partial adjustments, we need to proportionally adjust both taxable and withholding amounts
				values_to_update["withholding_amount"] = old_entry.withholding_amount * proportion
				values_to_update["taxable_amount"] = old_entry.taxable_amount * proportion

				# If tax rate has changed, recalculate based on new rate
				if self.tax_rate != old_entry.tax_rate:
					if not self.tax_rate:
						# Zero rate means no withholding
						values_to_update["withholding_amount"] = 0
					else:
						values_to_update["taxable_amount"] = flt(
							values_to_update["withholding_amount"] * 100 / self.tax_rate,
							precision,
						)

				new_entry = frappe.copy_doc(old_entry)
				new_entry.update(values_to_update)
				new_entry.insert()

				docs_needing_reindex.add((old_entry.parenttype, old_entry.parent))

			remaining_amount -= amount_we_can_match

			if remaining_amount <= 0:
				break

		else:
			frappe.throw(
				_("Row #{0}: Could not find enough {1} entries to match. Remaining amount: {2}").format(
					self.idx, status_to_find, remaining_amount
				)
			)
		_reset_idx(docs_needing_reindex)

	def _get_values_to_update(self, old_entry, proportion: float, field_type: str):
		field_to_update = "withholding" if field_type == "taxable" else "taxable"

		values = {
			f"{field_to_update}_amount": self.get(f"{field_to_update}_amount") * proportion,
			f"{field_to_update}_doctype": self.get(f"{field_to_update}_doctype"),
			f"{field_to_update}_name": self.get(f"{field_to_update}_name"),
			f"{field_to_update}_date": self.get(f"{field_to_update}_date"),
			"tax_rate": self.tax_rate,
			"status": "Duplicate",
			"under_withheld_reason": None,
		}

		if field_to_update == "taxable":
			values.update(
				currency=self.currency,
				conversion_rate=self.conversion_rate,
				under_withheld_reason=self.under_withheld_reason,
				lower_deduction_certificate=self.lower_deduction_certificate,
			)

		# NOTE: Allow offsetting across different categories
		# Update Tax Withholding Category values

		return values

	def _get_balance_values_to_update(self, old_entry, proportion: float, field_type: str):
		"""Calculate the balance amounts for both taxable and withholding fields for partial adjustments"""
		field_to_update = "withholding" if field_type == "taxable" else "taxable"
		field = f"{field_to_update}_amount"
		proportion = 1 - proportion

		amount = flt(old_entry.get(field) * proportion, self.precision(field))

		return {field: amount}

	# CANCEL
	def _clear_old_references(self):
		if self.status not in ["Settled", "Duplicate"]:
			return

		filters = {
			"tax_withholding_category": self.tax_withholding_category,
			"taxable_doctype": self.taxable_doctype,
			"taxable_name": self.taxable_name,
			"withholding_doctype": self.withholding_doctype,
			"withholding_name": self.withholding_name,
			"name": ["!=", self.name],
			"docstatus": 1,
		}

		if self.is_taxable_different:
			frappe.db.set_value(
				DOCTYPE,
				filters,
				{
					"withholding_name": "",
					"withholding_doctype": "",
					"withholding_amount": 0,
					"withholding_date": None,
					"under_withheld_reason": "",
					"lower_deduction_certificate": "",
					"status": "Under Withheld",
				},
			)

		elif self.is_withholding_different:
			if self.taxable_amount < 0:
				# Special handling for return invoice cancellation
				self._handle_return_invoice_cancellation(filters)
			else:
				frappe.db.set_value(
					DOCTYPE,
					filters,
					{
						"taxable_name": "",
						"taxable_doctype": "",
						"taxable_date": None,
						"status": "Over Withheld",
					},
				)

	def _handle_return_invoice_cancellation(self, filters):
		# Get old entries that need adjustment - inspired by _adjust_against_old_entries
		old_entries = frappe.get_all(
			DOCTYPE,
			filters=filters,
			fields="*",
		)

		docs_needing_reindex = set()

		for entry in old_entries:
			frappe.db.set_value(
				DOCTYPE,
				entry.name,
				{
					"taxable_doctype": entry.withholding_doctype,
					"taxable_name": entry.withholding_name,
					"taxable_date": entry.withholding_date,
				},
			)

			# cases where withholding amount is zero
			if entry.withholding_amount == 0:
				continue

			new_entry = frappe.copy_doc(frappe.get_doc(DOCTYPE, **entry))
			values_to_update = {
				"taxable_amount": abs(entry.taxable_amount),
				"withholding_amount": 0,
				"status": "Under Withheld",
				"under_withheld_reason": "",
				"taxable_doctype": entry.withholding_doctype,
				"taxable_name": entry.withholding_name,
				"taxable_date": entry.withholding_date,
				"withholding_doctype": "",
				"withholding_name": "",
				"withholding_date": None,
			}
			new_entry.update(values_to_update)
			new_entry.insert()

			docs_needing_reindex.add((entry.parenttype, entry.parent))

		_reset_idx(docs_needing_reindex)


from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	TaxWithholdingDetails,
	get_tax_id_for_party,
)


class TaxWithholdingController:
	def __init__(self, doc):
		self.doc = doc
		self.entries = []
		self.precision = self.doc.precision("withholding_amount", "tax_withholding_entries")

	def _get_category_details(self):
		"""Get tax withholding category details for the current document"""
		category_names = self._get_category_names()

		return TaxWithholdingDetails(
			category_names,
			self.doc.tax_withholding_group,
			self.doc.posting_date,
			self.party_type,
			self.party,
			self.doc.company,
		).get()

	def _get_category_names(self):
		category_names = set(
			item.tax_withholding_category
			for item in self.doc.items
			if item.tax_withholding_category and item.apply_tds
		)

		return category_names

	def calculate(self):
		self.category_details = self._get_category_details()

		self._update_taxable_amounts()

		if not self.doc.override_tax_withholding_entries:
			self._generate_withholding_entries()

		self._process_withholding_entries()

	def _generate_withholding_entries(self):
		self.doc.tax_withholding_entries = []

		self._evaluate_thresholds()

		for category in self.category_details.values():
			self.entries += self._create_entries_for_category(category)

		self.doc.extend("tax_withholding_entries", self.entries)

	def _create_entries_for_category(self, category):
		entries = []

		if not category.taxable_amount:
			return entries

		# Case 1: Threshold not crossed - create under withheld entry
		if not category.threshold_crossed:
			entries.append(self._create_under_withheld_entry(category))
			category.taxable_amount = 0
			return entries

		# Case 2: Tax on excess amount - handle threshold exemption first
		if category.unused_threshold:
			entries.append(self._create_threshold_exemption_entry(category))
			if category.taxable_amount <= 0:
				return entries

		# Case 3: Process remaining amount with historical entries
		open_entries = self._get_open_entries_for_category(category)
		under_entries = open_entries["under_withheld"]
		over_entries = open_entries["over_withheld"]

		# Case 4: Adjust Under and Over Withheld Entries
		entries.extend(self._adjust_under_over_withheld(under_entries, over_entries, category))

		# Case 4: Lower Deduction Certificate processing
		if category.ldc_unutilized_amount:
			entries.extend(self._process_ldc_entries(under_entries, over_entries, category))

		# Case 5: Regular tax withholding processing
		entries.extend(self._merge_entries(under_entries, over_entries, category))

		return entries

	def _create_under_withheld_entry(self, category):
		"""Create an under withheld entry when threshold is not crossed"""
		return {
			**self._create_default_entry(category),
			"taxable_amount": category.taxable_amount,
			"withholding_doctype": "",
			"withholding_name": "",
			"withholding_date": "",
			"withholding_amount": 0,
		}

	def _create_threshold_exemption_entry(self, category):
		"""Create entry for amount below threshold (tax on excess)"""
		taxable_amount = min(category.unused_threshold, category.taxable_amount)
		category.taxable_amount -= taxable_amount

		return {
			**self._create_default_entry(category),
			"taxable_amount": taxable_amount,
			"under_withheld_reason": "Threshold Exemption",
		}

	def _get_open_entries_for_category(self, category):
		"""Get historical under withheld and over withheld entries for processing"""
		entries = self._get_historical_entries(category)
		linked_payments = self._get_linked_payments()

		open_entries = {"under_withheld": deque(), "over_withheld": deque()}

		# Process historical entries
		self._categorize_historical_entries(entries, linked_payments, open_entries)

		# Add current document as under withheld
		current_entry = self._create_default_entry(category)
		current_entry.update(
			{
				"taxable_amount": category.taxable_amount,
				"withholding_doctype": "",
				"withholding_name": "",
				"withholding_date": "",
			}
		)
		open_entries["under_withheld"].appendleft(current_entry)

		return open_entries

	def _categorize_historical_entries(self, entries, linked_payments, open_entries):
		"""Categorize historical entries into under withheld and over withheld"""
		for entry in entries:
			if entry.status == "Under Withheld":
				open_entries["under_withheld"].append(entry)
				continue

			# Handle over withheld entries
			key = (entry.withholding_doctype, entry.withholding_name)
			if key in linked_payments:
				# Calculate proportion for linked payments
				# TODO: whether it should be entry.taxable_amount only or do we need proportion
				total_value = entry.taxable_amount - entry.withholding_amount
				if not total_value:
					continue
				proportion = linked_payments[key] / total_value

				# for handling rounding adjustments
				proportion = min(proportion, 1)
				entry.withholding_amount *= proportion
				open_entries["over_withheld"].appendleft(entry)
				continue

			# only linked payment entries are allowed
			if entry.withholding_doctype in ["Payment Entry", "Journal Entry"]:
				continue

			open_entries["over_withheld"].append(entry)

	def _process_ldc_entries(self, under_entries, over_entries, category):
		ldc_config = {
			"under_withheld_reason": "Lower Deduction Certificate",
			"lower_deduction_certificate": category.ldc_certificate,
		}

		return self._merge_entries(
			under_entries,
			over_entries,
			category,
			tax_rate=category.ldc_rate,
			constraint=category.ldc_unutilized_amount,
			default_obj=ldc_config,
		)

	def _update_taxable_amounts(self):
		if not self.doc.base_net_total:
			return

		self._update_amount_for_item()

	def _update_amount_for_item(self):
		precision = self.doc.precision("base_net_rate", "items")
		self._update_item_wise_tax_amount()

		for item in self.doc.get("items"):
			if not (item.apply_tds and item.tax_withholding_category):
				continue

			category = self.category_details.get(item.tax_withholding_category)

			if category.tax_deduction_basis != "Gross Total":
				taxable_amount = item.base_net_amount
			else:
				taxable_amount = item.base_net_amount + item._item_total_tax_amount

			taxable_amount = flt(taxable_amount, precision)

			item._base_tax_withholding_net_total = taxable_amount

			category["taxable_amount"] += flt(taxable_amount, precision)

	def _update_item_wise_tax_amount(self):
		for item in self.doc.get("items"):
			item._item_total_tax_amount = 0

		precision = self.doc.precision("tax_amount", "taxes")
		for row in self.doc.get("_item_wise_tax_details", []):
			item = row.item

			if not (item.apply_tds and item.tax_withholding_category):
				continue

			if row.tax.is_tax_withholding_account:
				continue

			item._item_total_tax_amount = flt(item._item_total_tax_amount + row.amount, precision)

	def _evaluate_thresholds(self):
		"""
		Evaluate if thresholds are crossed for each category

		Thresholds are crossed when:
		- Single transaction threshold is exceeded
		- Cumulative threshold is exceeded
		- Threshold check is manually overridden
		"""
		for category in self.category_details.values():
			category.threshold_crossed = self._is_threshold_crossed_for_category(category)
			category.unused_threshold = self._get_unused_threshold(category)

	def _is_threshold_crossed_for_category(self, category):
		# Manual override - always cross threshold
		if self.doc.ignore_tax_withholding_threshold:
			return True

		# Transaction threshold only mode
		if category.disable_cumulative_threshold:
			return category.taxable_amount >= category.single_threshold

		# No cumulative threshold set
		if category.cumulative_threshold == 0:
			return True

		# Tax on excess amount - always process
		if category.tax_on_excess_amount:
			return True

		# Standard cumulative/transaction threshold check
		return self._check_historical_threshold_status(category)

	def _check_historical_threshold_status(self, category):
		entry = frappe.qb.DocType(DOCTYPE)
		result = frappe._dict(
			self._base_threshold_query(category).where(entry.status.isin(["Settled", "Under Withheld"])).run()
		)

		# NOTE: Once deducted, always deducted. Not checking cumulative threshold again purposefully.
		# conservative approach to avoid tax disputes as it can have conflicting views
		# https://www.taxtmi.com/forum/issue?id=118627

		if result.get("Settled", 0) > 0:
			return True

		# Check remaining threshold
		remaining_threshold = category.cumulative_threshold - result.get("Under Withheld", 0)

		if not category.disable_transaction_threshold:
			remaining_threshold = min(remaining_threshold, category.single_threshold)

		return category.taxable_amount >= remaining_threshold

	def _get_unused_threshold(self, category):
		"""Calculate unused threshold amount for tax on excess scenarios"""
		if not category.tax_on_excess_amount:
			return 0

		entry = frappe.qb.DocType(DOCTYPE)
		result = frappe._dict(
			self._base_threshold_query(category)
			.where(IfNull(entry.under_withheld_reason, "") == "Threshold Exemption")
			.run()
		)

		return category.cumulative_threshold - result.get("Settled", 0)

	def _base_threshold_query(self, category):
		entry = frappe.qb.DocType(DOCTYPE)
		query = (
			frappe.qb.from_(entry)
			.select(entry.status, Sum(entry.taxable_amount).as_("taxable_amount"))
			.where(entry.party_type == self.party_type)
			.where(entry.tax_withholding_category == category.name)
			.where(entry.company == self.doc.company)
			.where(entry.docstatus == 1)
			.groupby(entry.status)
		)

		# NOTE: This can be a configurable option
		# To check if filter by tax_id is needed
		tax_id = get_tax_id_for_party(self.party_type, self.party)
		query = query.where(entry.tax_id == tax_id) if tax_id else query.where(entry.party == self.party)

		return query

	def _get_historical_entries(self, category):
		entry = frappe.qb.DocType(DOCTYPE)
		base_query = (
			frappe.qb.from_(entry)
			.select("*")
			.where(entry.tax_withholding_category == category.name)
			.where(entry.party_type == self.party_type)
			.where(entry.party == self.party)
			.where(entry.company == self.doc.company)
			.where(entry.docstatus == 1)
		)

		over_withheld_query = base_query.where(entry.status == "Over Withheld")

		return (
			base_query.where(entry.status == "Under Withheld")
			.where(entry.taxable_date.between(category.from_date, category.to_date))
			.union(over_withheld_query)
			.run(as_dict=True)
		)

	def _get_linked_payments(self):
		references = frappe._dict()
		for ref in self.doc.advances:
			key = (ref.reference_type, ref.reference_name)
			references[key] = ref.allocated_amount * self.doc.conversion_rate

		return references

	def _create_default_entry(self, category):
		return frappe._dict(
			{
				"company": self.doc.company,
				"party_type": self.party_type,
				"party": self.party,
				"tax_withholding_category": category.name,
				"tax_withholding_group": category.tax_withholding_group,
				"tax_rate": category.tax_rate,
				"conversion_rate": self.get_conversion_rate(),
				"taxable_doctype": self.doc.doctype,
				"taxable_name": self.doc.name,
				"taxable_date": self.doc.posting_date,
				"taxable_amount": 0,
				"withholding_doctype": self.doc.doctype,
				"withholding_name": self.doc.name,
				"withholding_date": self.doc.posting_date,
				"withholding_amount": 0,  # Will be computed later
			}
		)

	def update_tax_rows(self):
		"""Update tax rows in the parent document based on withholding entries"""
		account_amount_map = self._calculate_account_wise_amount()
		category_withholding_map = self._get_category_withholding_map()
		existing_taxes = {row.account_head: row for row in self.doc.taxes if row.is_tax_withholding_account}
		precision = self.doc.precision("tax_amount", "taxes")
		conversion_rate = self.get_conversion_rate()
		add_deduct_tax = "Deduct"

		if self.party_type == "Customer":
			add_deduct_tax = "Add"

		for account_head, base_amount in account_amount_map.items():
			tax_amount = flt(base_amount / conversion_rate, precision)
			if not tax_amount:
				continue

			# Update existing tax row or create new one
			if existing_tax := existing_taxes.get(account_head):
				existing_tax.tax_amount = tax_amount
				existing_tax.dont_recompute_tax = 1
				tax_row = existing_tax
				for_update = True
			else:
				tax_row = self._create_tax_row(account_head, tax_amount)
				for_update = False

			tax_row.add_deduct_tax = add_deduct_tax
			# Set item-wise tax breakup for this tax row
			self._set_item_wise_tax_for_tds(
				tax_row, account_head, category_withholding_map, for_update=for_update
			)

		self._remove_zero_tax_rows()
		self.calculate_taxes_and_totals()

	def _create_tax_row(self, account_head, tax_amount):
		cost_center = self.doc.cost_center or erpnext.get_default_cost_center(self.doc.company)
		return self.doc.append(
			"taxes",
			{
				"is_tax_withholding_account": 1,
				"category": "Total",
				"charge_type": "Actual",
				"account_head": account_head,
				"description": account_head,
				"cost_center": cost_center,
				"tax_amount": tax_amount,
				"dont_recompute_tax": 1,
			},
		)

	def _set_item_wise_tax_for_tds(self, tax_row, account_head, category_withholding_map, for_update=False):
		# Get all categories for this account (multiple categories can share same account)
		categories_for_account = [
			cat for cat in self.category_details.values() if cat.account_head == account_head
		]

		if not categories_for_account:
			return

		if not hasattr(self.doc, "_item_wise_tax_details"):
			self.doc._item_wise_tax_details = []

		if for_update:
			self.doc._item_wise_tax_details = [
				d for d in self.doc._item_wise_tax_details if d.get("tax") != tax_row
			]

		items = self.doc.get("items") or []
		category_totals = {}
		for item in items:
			if item.apply_tds and item.tax_withholding_category:
				item_taxable = item.get("_base_tax_withholding_net_total", 0)
				category_totals[item.tax_withholding_category] = (
					category_totals.get(item.tax_withholding_category, 0) + item_taxable
				)

		precision = self.doc.precision("tax_amount", "taxes")
		for item in items:
			if not (item.apply_tds and item.tax_withholding_category):
				continue

			category = self.category_details.get(item.tax_withholding_category)
			if not category or category.account_head != account_head:
				continue

			item_base_taxable = item.get("_base_tax_withholding_net_total") or 0

			if not category.taxable_amount or not item_base_taxable:
				continue

			total_taxable_amount = category_totals.get(category.name, 0)

			if category.unused_threshold and total_taxable_amount:
				# Proportionately deduct unused threshold from item's base taxable
				item_threshold_deduction = (
					item_base_taxable / total_taxable_amount
				) * category.unused_threshold
				item_effective_taxable = max(0, item_base_taxable - item_threshold_deduction)
			else:
				item_effective_taxable = item_base_taxable

			withholding_amount = category_withholding_map.get(category.name, 0)
			if withholding_amount and category.taxable_amount:
				item_proportion = item_effective_taxable / category.taxable_amount
				item_tax_amount = flt(withholding_amount * item_proportion, precision)
			else:
				item_tax_amount = 0

			multiplier = -1 if tax_row.add_deduct_tax == "Deduct" else 1

			self.doc._item_wise_tax_details.append(
				frappe._dict(
					item=item,
					tax=tax_row,
					rate=category.tax_rate,
					amount=item_tax_amount * multiplier,
					taxable_amount=item_base_taxable,
				)
			)

	def _get_category_withholding_map(self):
		category_withholding_map = defaultdict(float)

		for entry in self.doc.tax_withholding_entries:
			if entry.withholding_name != self.doc.name:
				continue
			category_withholding_map[entry.tax_withholding_category] += entry.withholding_amount

		return category_withholding_map

	def _calculate_account_wise_amount(self):
		account_amount_map = defaultdict(float)

		for entry in self.doc.tax_withholding_entries:
			if entry.withholding_name != self.doc.name:
				continue
			category = self.category_details.get(entry.tax_withholding_category)
			account_amount_map[category.account_head] += entry.withholding_amount

		return account_amount_map

	def _remove_zero_tax_rows(self):
		self.doc.taxes = [
			row for row in self.doc.taxes if not (row.is_tax_withholding_account and not row.tax_amount)
		]

	def _adjust_under_over_withheld(
		self,
		under_entries: deque,
		over_entries: deque,
		category: dict,
	):
		"""
		Merge under withheld and over withheld entries based on the tax rate and constraint.
		If only under and over entries are available, they will be processed against current document.
		"""
		if not (under_entries and over_entries):
			return []

		merged_entries = []

		while under_entries and over_entries:
			under = under_entries[0]
			over = over_entries[0]
			tax_rate = over.tax_rate

			# Calculate tax amount for this taxable amount
			tax_amount = self.compute_withheld_amount(
				under.taxable_amount,
				tax_rate,
				round_off_tax_amount=category.round_off_tax_amount,
			)

			tax_amount = flt(min(tax_amount, over.withholding_amount), self.precision)

			if tax_rate == 0:
				taxable_amount = min(under.taxable_amount, over.taxable_amount)
			else:
				taxable_amount = flt(100 / tax_rate * tax_amount, self.precision)

			# Create merged entry
			merged_entry = under.copy()
			merged_entry.update(
				{
					"taxable_amount": taxable_amount,
					"withholding_amount": tax_amount,
					"withholding_doctype": over.withholding_doctype,
					"withholding_name": over.withholding_name,
					"withholding_date": over.withholding_date,
					"under_withheld_reason": over.under_withheld_reason,
					"tax_rate": tax_rate,
					"lower_deduction_certificate": over.lower_deduction_certificate,
				}
			)

			# Consolidate entries by document combination
			if self._should_include_entry(merged_entry):
				merged_entries.append(merged_entry)

			under.taxable_amount -= taxable_amount
			over.withholding_amount -= tax_amount

			if flt(under.taxable_amount, self.precision) <= 0:
				under_entries.popleft()
			if flt(over.withholding_amount, self.precision) <= 0:
				over_entries.popleft()

		return merged_entries

	def _merge_entries(
		self,
		under_entries: deque,
		over_entries: deque,
		category: dict,
		tax_rate: float | None = None,
		constraint: float = inf,
		default_obj: dict | None = None,
	):
		"""
		Merge under withheld and over withheld entries based on the tax rate and constraint.
		If only under and over entries are available, they will be processed against current document.
		"""
		merged_entries = []
		if not ((under_entries or over_entries) and constraint > 0):
			return merged_entries

		if tax_rate is None:
			tax_rate = category.tax_rate

		# Process remaining under entries
		constraint = self._process_under_withheld_entries(
			under_entries, category, tax_rate, constraint, default_obj, merged_entries
		)

		# Process remaining over entries
		self._process_over_withheld_entries(
			over_entries, category, tax_rate, constraint, default_obj, merged_entries
		)

		return merged_entries

	def _process_under_withheld_entries(
		self, under_entries, category, tax_rate, constraint, default_obj, merged_entries
	):
		"""
		Process remaining Under Withheld Entries - adjust against current document
		"""
		while under_entries and constraint > 0:
			entry = under_entries[0]

			value_direction = -1 if entry.taxable_amount < 0 else 1
			amount_to_process = min(entry.taxable_amount, constraint)

			if amount_to_process * value_direction <= 0:
				break

			# Create base entry and calculate withholding amount
			merged_entry = self._create_base_entry(entry, category, tax_rate, default_obj)
			merged_entry.update(
				{
					"taxable_amount": flt(amount_to_process, self.precision),
					"withholding_amount": self.compute_withheld_amount(
						amount_to_process,
						tax_rate,
						round_off_tax_amount=category.round_off_tax_amount,
					),
					"withholding_doctype": self.doc.doctype,
					"withholding_name": self.doc.name,
					"withholding_date": self.doc.posting_date,
				}
			)

			# Always include under entries
			merged_entries.append(merged_entry)

			# Update entry amounts
			entry.taxable_amount -= amount_to_process
			if flt(entry.taxable_amount * value_direction, self.precision) <= 0:
				under_entries.popleft()

			# Update constraint
			constraint -= amount_to_process

		return constraint

	def _process_over_withheld_entries(
		self, over_entries, category, tax_rate, constraint, default_obj, merged_entries
	):
		"""
		Process remaining Over Withheld Entries - adjust existing over-withheld amounts
		"""
		while over_entries and constraint > 0:
			entry = over_entries[0]

			value_direction = -1 if entry.taxable_amount < 0 else 1
			amount_to_process = min(entry.taxable_amount, constraint)

			if amount_to_process * value_direction <= 0:
				break

			# Create base entry and calculate withholding amount
			merged_entry = self._create_base_entry(entry, category, tax_rate, default_obj)
			merged_entry.update(
				{
					"taxable_amount": flt(amount_to_process, self.precision),
					"withholding_amount": self.compute_withheld_amount(
						amount_to_process,
						tax_rate,
						round_off_tax_amount=category.round_off_tax_amount,
					),
					"withholding_doctype": entry.withholding_doctype,
					"withholding_name": entry.withholding_name,
					"withholding_date": entry.withholding_date,
					"taxable_doctype": "",
					"taxable_name": "",
					"taxable_date": "",
					"conversion_rate": self.get_conversion_rate(),
				}
			)

			# Only include over entries related to current document
			if self._should_include_entry(merged_entry):
				merged_entries.append(merged_entry)

			# Update entry amounts
			entry.taxable_amount -= amount_to_process
			if flt(entry.taxable_amount * value_direction, self.precision) <= 0:
				over_entries.popleft()

			# Update constraint
			constraint -= amount_to_process

		return constraint

	def _create_base_entry(self, source_entry, category, tax_rate, default_obj):
		entry = {}
		if default_obj:
			entry.update(default_obj)

		entry.update(
			{
				"taxable_doctype": source_entry.taxable_doctype,
				"taxable_name": source_entry.taxable_name,
				"taxable_date": source_entry.taxable_date,
				"tax_withholding_category": category.name,
				"tax_rate": tax_rate,
				"party_type": self.party_type,
				"party": self.party,
				"company": self.doc.company,
			}
		)
		return entry

	def _should_include_entry(self, entry):
		return entry.get("taxable_name") == self.doc.name or entry.get("withholding_name") == self.doc.name

	def compute_withheld_amount(self, taxable_amount, tax_rate, round_off_tax_amount=False):
		"""Calculate the withholding amount based on taxable amount and rate"""
		amount = taxable_amount * tax_rate / 100
		if round_off_tax_amount:
			return flt(amount, 0)
		return flt(amount, self.precision)

	def _process_withholding_entries(self):
		"""Final processing - update tax rows and validate"""
		self.update_tax_rows()
		for entry in self.doc.tax_withholding_entries:
			entry: TaxWithholdingEntry
			entry.set_status(entry.status)
			entry.validate_adjustments()
			entry.validate_tax_withheld_amount()

	def on_submit(self):
		for entry in self.doc.tax_withholding_entries:
			entry: TaxWithholdingEntry
			entry._process_tax_withholding_adjustments()

	def on_cancel(self):
		for entry in self.doc.tax_withholding_entries:
			entry: TaxWithholdingEntry
			entry._clear_old_references()
			entry.set_status()

	def _is_tax_withholding_applicable(self):
		# Clear existing tax withholding amounts before recalculation
		self._clear_existing_tax_amounts()

		if not self.doc.apply_tds or self.doc.get("is_opening") == "Yes" or not self._get_category_names():
			self.doc.tax_withholding_entries = []
			return False

		return True

	def _clear_existing_tax_amounts(self):
		for row in self.doc.taxes:
			if row.is_tax_withholding_account and row.tax_amount:
				row.tax_amount = 0
				row.base_tax_amount_after_discount_amount = 0

	def calculate_taxes_and_totals(self):
		self.doc.calculate_taxes_and_totals()

	def get_conversion_rate(self):
		return self.doc.get("conversion_rate") or 1

	def on_validate(self):
		if self._is_tax_withholding_applicable():
			self.calculate()


class PurchaseTaxWithholding(TaxWithholdingController):
	"""Tax withholding controller for Purchase Invoices"""

	def __init__(self, doc):
		super().__init__(doc)
		self.party_type = "Supplier"
		self.party = doc.supplier


class SalesTaxWithholding(TaxWithholdingController):
	"""Tax withholding controller for Sales Invoices (TCS)"""

	def __init__(self, doc):
		super().__init__(doc)
		self.party_type = "Customer"
		self.party = doc.customer


class PaymentTaxWithholding(TaxWithholdingController):
	"""Tax withholding controller for Payment Entries"""

	def __init__(self, doc):
		super().__init__(doc)
		self.party_type = doc.party_type
		self.party = doc.party

	def _get_category_names(self):
		if not self.doc.tax_withholding_category:
			return []

		return [self.doc.tax_withholding_category]

	def _update_taxable_amounts(self):
		category = next(iter(self.category_details.values()))

		taxable_amount_in_party_currency = self.doc.unallocated_amount
		taxable_amount_in_party_currency += sum(
			flt(d.allocated_amount)
			for d in self.doc.references
			if d.reference_doctype in get_advance_payment_doctypes()
		)

		exchange_rate = self.get_conversion_rate()
		taxable_amount = flt(taxable_amount_in_party_currency * exchange_rate, self.precision)

		category["taxable_amount"] = taxable_amount

	def get_conversion_rate(self):
		if self.doc.payment_type == "Receive":
			return self.doc.source_exchange_rate or 1
		else:
			return self.doc.target_exchange_rate or 1

	def calculate_taxes_and_totals(self):
		self.doc.apply_taxes()

	def _get_open_entries_for_category(self, category):
		# for payment only over withheld
		open_entries = {"under_withheld": deque(), "over_withheld": deque()}

		current_entry = frappe._dict(
			{
				**self._create_default_entry(category),
				"taxable_amount": category.taxable_amount,
				"taxable_doctype": "",
				"taxable_name": "",
				"taxable_date": "",
			}
		)

		open_entries["over_withheld"].append(current_entry)

		return open_entries

	def _is_threshold_crossed_for_category(self, category):
		"""For payment entries if apply_tds is checked, return True"""
		return True

	def _get_unused_threshold(self, category):
		"""Always withhold Tax and whenever tax gets deducted adjust it"""
		return 0


class JournalTaxWithholding(TaxWithholdingController):
	"""Tax withholding controller for Journal Entries"""

	def __init__(self, doc):
		super().__init__(doc)
		self.party = None
		self.party_type = None
		self.party_account = None
		self.party_row = None
		self.existing_tds_rows = []
		self.precision = None
		self.has_multiple_parties = False

		self.party_field = None
		self.reverse_field = None

		self._setup_party_info()

	def _setup_party_info(self):
		for row in self.doc.get("accounts"):
			if row.party_type in ("Customer", "Supplier") and row.party:
				if self.party and row.party != self.party:
					self.has_multiple_parties = True

				if not self.party:
					self.party = row.party
					self.party_type = row.party_type
					self.party_account = row.account
					self.party_row = row

			if row.get("is_tax_withholding_account"):
				self.existing_tds_rows.append(row)

		if self.party_type:
			self._setup_direction_fields()

	def _setup_direction_fields(self):
		"""
		For Supplier (TDS): party has credit, TDS reduces credit
		For Customer (TCS): party has debit, TCS increases debit
		"""
		if self.party_type == "Supplier":
			self.party_field = "credit"
			self.reverse_field = "debit"
		else:  # Customer
			self.party_field = "debit"
			self.reverse_field = "credit"

		self.precision = self.doc.precision(self.party_field, self.party_row)

	def _get_category_names(self):
		if not self.doc.tax_withholding_category:
			return []

		return [self.doc.tax_withholding_category]

	def _update_taxable_amounts(self):
		if not self.category_details:
			return

		net_amount = self._calculate_net_total()
		category = next(iter(self.category_details.values()))
		category["taxable_amount"] = net_amount

	def _calculate_net_total(self):
		from erpnext.accounts.report.general_ledger.general_ledger import get_account_type_map

		account_type_map = get_account_type_map(self.doc.company)

		return flt(
			sum(
				d.get(self.reverse_field) - d.get(self.party_field)
				for d in self.doc.get("accounts")
				if account_type_map.get(d.account) not in ("Tax", "Chargeable")
				and d.account != self.party_account
				and not d.get("is_tax_withholding_account")
			),
			self.precision,
		)

	def get_conversion_rate(self):
		return self.party_row.get("exchange_rate", 1.0)

	def calculate_taxes_and_totals(self):
		self.doc.set_amounts_in_company_currency()
		self.doc.set_total_debit_credit()
		self.doc.set_against_account()

	def update_tax_rows(self):
		if not self._should_apply_tds():
			self._cleanup_duplicate_tds_rows(None)
			return

		if self.has_multiple_parties:
			frappe.throw(_("Cannot apply TDS against multiple parties in one entry"))

		account_amount_map = self._calculate_account_wise_amount()

		if not account_amount_map:
			return

		self._reset_existing_tds()

		for account_head, tax_amount in account_amount_map.items():
			if not tax_amount:
				continue

			self._create_or_update_tds_row(account_head, tax_amount)
			self._update_party_amount(tax_amount, is_reversal=False)

		self._recalculate_totals()

	def _should_apply_tds(self):
		return self.doc.apply_tds and self.doc.voucher_type in ("Debit Note", "Credit Note")

	def _reset_existing_tds(self):
		for row in self.existing_tds_rows:
			# TDS amount is always in credit (liability to government)
			tds_amount = flt(row.get("credit") - row.get("debit"), self.precision)
			if not tds_amount:
				continue

			self._update_party_amount(tds_amount, is_reversal=True)

			# zero_out_tds_row
			row.update(
				{
					"credit": 0,
					"credit_in_account_currency": 0,
					"debit": 0,
					"debit_in_account_currency": 0,
				}
			)

	def _update_party_amount(self, amount, is_reversal=False):
		amount = flt(amount, self.precision)
		amount_in_party_currency = flt(amount / self.party_row.get("exchange_rate", 1), self.precision)

		# Determine which field the party amount is in
		active_field = self.party_field if self.party_row.get(self.party_field) else self.reverse_field

		# If amount is in reverse field, flip the signs
		if active_field == self.reverse_field:
			amount = -amount
			amount_in_party_currency = -amount_in_party_currency

		# Direction multiplier based on party type:
		# Customer (TCS): +1 (add to debit)
		# Supplier (TDS): -1 (subtract from credit)
		direction = 1 if self.party_type == "Customer" else -1

		# Reversal inverts the direction
		if is_reversal:
			direction = -direction

		adjustment = amount * direction
		adjustment_in_party_currency = amount_in_party_currency * direction

		active_field_account_currency = f"{active_field}_in_account_currency"

		self.party_row.update(
			{
				active_field: flt(self.party_row.get(active_field) + adjustment, self.precision),
				active_field_account_currency: flt(
					self.party_row.get(active_field_account_currency) + adjustment_in_party_currency,
					self.precision,
				),
			}
		)

	def _create_or_update_tds_row(self, account_head, tax_amount):
		from erpnext.accounts.utils import get_account_currency
		from erpnext.setup.utils import get_exchange_rate as _get_exchange_rate

		account_currency = get_account_currency(account_head)
		company_currency = frappe.get_cached_value("Company", self.doc.company, "default_currency")
		exchange_rate = _get_exchange_rate(account_currency, company_currency, self.doc.posting_date)

		tax_amount = flt(tax_amount, self.precision)
		tax_amount_in_account_currency = flt(tax_amount / exchange_rate, self.precision)

		tax_row = None
		for row in self.doc.get("accounts"):
			if row.account == account_head and row.get("is_tax_withholding_account"):
				tax_row = row
				break

		if not tax_row:
			tax_row = self.doc.append(
				"accounts",
				{
					"account": account_head,
					"account_currency": account_currency,
					"exchange_rate": exchange_rate,
					"cost_center": self.doc.get("cost_center")
					or erpnext.get_default_cost_center(self.doc.company),
					"credit": 0,
					"credit_in_account_currency": 0,
					"debit": 0,
					"debit_in_account_currency": 0,
					"is_tax_withholding_account": 1,
				},
			)

		# TDS/TCS is always credited (liability to government)
		tax_row.update(
			{
				"credit": tax_amount,
				"credit_in_account_currency": tax_amount_in_account_currency,
				"debit": 0,
				"debit_in_account_currency": 0,
			}
		)

		self._cleanup_duplicate_tds_rows(tax_row)

	def _cleanup_duplicate_tds_rows(self, current_tax_row):
		rows_to_remove = [
			row
			for row in self.doc.get("accounts")
			if row.get("is_tax_withholding_account") and row != current_tax_row
		]

		for row in rows_to_remove:
			self.doc.remove(row)

	def _recalculate_totals(self):
		self.doc.set_amounts_in_company_currency()
		self.doc.set_total_debit_credit()
		self.doc.set_against_account()

	def _is_tax_withholding_applicable(self):
		if not self._should_apply_tds():
			self.doc.tax_withholding_entries = []
			return False

		if not self.doc.tax_withholding_category:
			self.doc.tax_withholding_entries = []
			return False

		return True

	def _get_linked_payments(self):
		"""Journal Entry doesn't have advances like invoices"""
		return frappe._dict()


def _reset_idx(docs_to_reset_idx):
	updates = {}
	for doctype, docname in docs_to_reset_idx:
		names = frappe.get_all(
			DOCTYPE,
			filters={"parent": docname, "parenttype": doctype, "docstatus": 1},
			pluck="name",
		)

		for idx, name in enumerate(names, start=1):
			updates[name] = {"idx": idx}

	if updates:
		frappe.db.bulk_update(DOCTYPE, updates, update_modified=False)
