# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict, deque
from math import inf

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# TODO: Should threshold check be reduced with purchase returns?

DOCTYPE = "Tax Withholding Entry"


class TaxWithholdingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_rate: DF.Float
		currency: DF.Link | None
		is_manual_override: DF.Check
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
		taxable_amount: DF.Currency
		taxable_date: DF.Date | None
		taxable_doctype: DF.Link | None
		taxable_name: DF.DynamicLink | None
		tw_tax_category: DF.Link | None
		under_withheld_reason: DF.Literal["", "Threshold Exemption", "Lower Deduction Certificate"]
		withholding_amount: DF.Currency
		withholding_date: DF.Date | None
		withholding_doctype: DF.Link | None
		withholding_name: DF.DynamicLink | None
	# end: auto-generated types

	def validate(self):
		self.set_status()
		self.validate_adjustments()

	def on_submit(self):
		self._process_tax_withholding_adjustments()

	def on_cancel(self):
		self._clear_old_references()

	def set_status(self, status=None):
		"""Update the status of this entry based on its current state"""
		if not status:
			status = self.get_status()

		self.status = status

	def get_status(self):
		"""Get the current status of this entry"""
		if self.docstatus == 2:
			return "Cancelled"

		# Reasons are genuine allowed reasons for short deduction.
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

	@property
	def is_taxable_different(self):
		return self.taxable_doctype != self.parenttype or self.taxable_name != self.parent

	@property
	def is_withholding_different(self):
		return self.withholding_doctype != self.parenttype or self.withholding_name != self.parent

	# SUBMIT

	def _process_tax_withholding_adjustments(self):
		# SCENARIO 1: Adjust against under-withheld entries (we have taxable amount, they need withholding)
		if self.is_taxable_different:
			self._adjust_against_old_entries(field_type="taxable")

		# SCENARIO 2: Adjust against over-withheld entries (we have withholding amount, they need taxable)
		elif self.is_withholding_different:
			self._adjust_against_old_entries(field_type="withholding")

	def _adjust_against_old_entries(self, field_type: str) -> set:
		"""
		Find old entries that need adjustment and update them.

		Args:
		        entry: The current entry we're submitting
		        field_type: Either "taxable" or "withholding" - determines which fields to use

		The logic reads like: "Match up old incomplete entries with this new entry"
		"""

		doctype_field = f"{field_type}_doctype"
		docname_field = f"{field_type}_name"
		amount_field = f"{field_type}_amount"
		status_to_find = "Under Withheld" if field_type == "taxable" else "Over Withheld"

		# Find old entries that need our help
		old_entries = frappe.get_all(
			DOCTYPE,
			filters={
				"tax_withholding_category": self.tax_withholding_category,
				"status": status_to_find,
				doctype_field: self.get(doctype_field),
				docname_field: self.get(docname_field),
			},
			fields="*",
		)

		value_direction = -1 if self.get(amount_field) < 0 else 1
		remaining_amount = abs(self.get(amount_field))
		docs_needing_reindex = set()

		# Go through each old entry and try to match it with our amount
		for old_entry_data in old_entries:
			old_entry = frappe.get_doc(DOCTYPE, **old_entry_data)
			old_amount = abs(old_entry.get(amount_field))

			if old_entry.get(amount_field) * value_direction < 0:
				# If the sign of the old entry's amount is different, we can't match it
				continue

			amount_we_can_match = min(old_amount, remaining_amount)  # Returns
			proportion = amount_we_can_match / old_amount if old_amount else 0
			values_to_update = self._get_values_to_update(proportion, field_type)

			if old_amount <= amount_we_can_match:
				# We can fully satisfy this old entry
				frappe.db.set_value(DOCTYPE, old_entry.name, values_to_update)

			else:
				# We can only partially satisfy this old entry - need to split it
				balance_amount = (old_amount - amount_we_can_match) * value_direction
				frappe.db.set_value(DOCTYPE, old_entry.name, {amount_field: balance_amount})

				new_entry = frappe.copy_doc(old_entry)
				new_entry.update(values_to_update)
				new_entry.insert()

				docs_needing_reindex.add((old_entry.parenttype, old_entry.parent))

			remaining_amount -= amount_we_can_match

			if remaining_amount <= 0:
				break

		else:
			# If we couldn't match all our amount, that's an error
			frappe.throw(
				_("Row #{0}: Could not find enough {1} entries to match. Remaining amount: {2}").format(
					self.idx, status_to_find, remaining_amount
				)
			)

		_reset_idx(docs_needing_reindex)

	def _get_values_to_update(self, proportion: float, field_type: str):
		field_to_update = "withholding" if field_type == "taxable" else "taxable"

		values = {
			f"{field_to_update}_amount": self.get(f"{field_to_update}_amount") * proportion,
			f"{field_to_update}_doctype": self.get(f"{field_to_update}_doctype"),
			f"{field_to_update}_name": self.get(f"{field_to_update}_name"),
			f"{field_to_update}_date": self.get(f"{field_to_update}_date"),
			"tax_rate": self.tax_rate,
			"is_manual_override": self.is_manual_override,
			"status": "Duplicate",
		}

		if field_to_update == "taxable":
			values.update(
				currency=self.currency,
				conversion_rate=self.conversion_rate,
				under_withheld_reason=self.under_withheld_reason,
				lower_deduction_certificate=self.lower_deduction_certificate,
			)

		return values

	# CANCEL

	def _clear_old_references(self):
		if self.is_taxable_different:
			frappe.db.set_value(
				DOCTYPE,
				{
					"tax_withholding_category": self.tax_withholding_category,
					"taxable_doctype": self.taxable_doctype,
					"taxable_name": self.taxable_name,
					"name": ["!=", self.name],
				},
				{
					"withholding_name": "",
					"withholding_doctype": "",
					"withholding_amount": 0,
					"status": "Under Withheld",
				},
			)

		elif self.is_withholding_different:
			frappe.db.set_value(
				DOCTYPE,
				{
					"tax_withholding_category": self.tax_withholding_category,
					"withholding_doctype": self.withholding_doctype,
					"withholding_name": self.withholding_name,
					"name": ["!=", self.name],
				},
				{
					"taxable_name": "",
					"taxable_doctype": "",
					"taxable_amount": 0,
					"status": "Over Withheld",
				},
			)


def _reset_idx(docs_to_reset_idx):
	updates = []
	for doctype, docname in docs_to_reset_idx:
		names = frappe.get_all(
			DOCTYPE,
			filters={"parent": docname, "parenttype": doctype},
			pluck="name",
		)

		for idx, name in enumerate(names, start=1):
			updates.append({"name": name, "idx": idx})

	frappe.db.bulk_update(DOCTYPE, updates, update_modified=False)


# Steps
# Create table in Purchase Invoice and Sales Invoice
# Update settings for TW Category
# Threshold overrides for party
# Only single threshold for TW Category

# Fetch tax details
# -- From Party at Document Level
# -- From Item at Item Level

# Calculate tax and set rows
# -- Determine tax categories and rates and thresholds with settings
# -- Calculate amount considering thresholds / lower deduction / gross or net

# Calculate amounts (taxable)
# -- Calculate net or gross amount for each item (excluding tds row) (document total less excluded items)
# -- Compute this for each tax category
# -- Determine tax rate (lower deduction)
# -- Calculate tax withheld (taxable amount * tax rate)

# If amount is deducted / deductible:
# -- Check for short deductions historically (ignore withholding doctype == payment entry)
# -- Check for excess deductions historically (from payment entry only if exisiting invoice is paid using it)
# -- Map them automatically in the entry

# Payment Entry
# -- Threshold check (existing amount is to be considered as tax inclusive)
# -- Short deduction rows are never included (??)
# -- Taxable amount is entered by user
# -- Tax Category is selected by user
# -- It's always excess deduction (tax amount is always 0 ??)

# Journal Entry
# -- Fetch tax details from party at account level
# -- Enable applicability at document level
# -- Apply TDS check

# -- Excess deduction is not possible
# -- Short deduction is allowed
# -- Taxable amount is determined as (party amount / (1-tax rate))
# -- Short or excess tax will be added to the last entry of the row

# Next Steps
# -- Cleanup
# -- Patch
# -- Tests
# -- Documentation

## What is allowed in manual override?
# -- Adjust taxable or tax withheld amount
# -- Cannot adjust (increase or decrease) taxable amount if taxable doctype is not the current document. Decrease not allowed as it will result in short deduction (historically).
# -- However, user can reduce the taxable amount in the original document.
# -- Cannot increase tax withheld amount if withholding doctype is not the current document

## How to respect user input for old adjustments?
# -- Short deductions will come automatically. Always
# -- Excess deductions will be applied only if TDS entries are not available in the current document.
# -- Current document should be there to the fullest extent (except manual override of taxable amount).


def on_invoice_validate(doc):
	if not doc.apply_tds:
		doc.tax_withholding_entries = []
		doc.tax_withholding_category = None
		# TODO: remove tds row from taxes table

		return

	TaxWithholdingController(doc).calculate()


from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_tax_withholding_categories,
)


class TaxWithholdingController:
	def __init__(self, doc):
		self.doc = doc
		self.party_type = "Supplier"
		self.party = doc.supplier
		self.entries = []

	def _get_category_details(self):
		"""Get tax withholding category details for the current document"""
		category_names = set(
			item.tax_withholding_category
			for item in self.doc.items
			if item.tax_withholding_category and item.apply_tds
		)
		if self.doc.tax_withholding_category:
			category_names.add(self.doc.tax_withholding_category)

		return get_tax_withholding_categories(
			category_names, self.doc.posting_date, self.party_type, self.party, self.doc.company
		)

	def calculate(self):
		"""Main orchestrator for tax withholding calculation"""
		# Step 1: Gather category details
		self.category_details = self._get_category_details()

		# Step 2: Calculate taxable amounts for each category
		self.set_category_wise_taxable_amount()

		# Step 3: Apply threshold rules
		self.evaluate_thresholds()

		# Step 4: Process each category
		for category in self.category_details.values():
			# Get the default entry template for this category
			default_entry = self._create_default_entry(category)

			# threshold not crossed
			if not category.threshold_crossed:
				entry = self._process_below_threshold_entry(category, default_entry)
				self.entries.append(entry)
				continue

			# tax on excess amount
			if category.untilized_threshold:
				entry = self._process_excess_threshold_entry(category, default_entry)
				self.entries.append(entry)

				if category.taxable_amount <= 0:
					continue

			open_entries = self.get_short_excess_entries(category)

			# ldc
			if category.ldc_unutilized_amount:
				default_obj = {
					"is_short_deduction": 1,
					"under_withheld_reason": "Lower Deduction Certificate",
					"lower_deduction_certificate": category.ldc_certificate,
				}
				merged = self._merge_entries(
					open_entries["short_deduction"],
					open_entries["excess_deduction"],
					category,
					tax_rate=category.ldc_rate,
					constraint=category.ldc_unutilized_amount,
					default_obj=default_obj,
				)

				self.entries.extend(merged)
				if not open_entries["short_deduction"]:
					continue

			merged = self._merge_entries(
				open_entries["short_deduction"], open_entries["excess_deduction"], category
			)

			self.entries.extend(merged)

		# Step 5: Process entries for existing document
		for entry in self.entries:
			if entry.get("withholding_name"):
				continue

			entry.update(
				withholding_doctype=self.doc.doctype,
				withholding_name=self.doc.name,
				withholding_date=self.doc.posting_date,
			)

		# Update tax rows in the parent document
		# TODO

	def set_category_wise_taxable_amount(self):
		if self.is_doc_level_calculation():
			self.update_taxable_value_based_on_doc()
		else:
			self.update_taxable_value_based_on_item()

	def update_taxable_value_based_on_doc(self):
		# only single cateory
		category = self.category_details[next(iter(self.category_details))]
		amount = 0
		if category.tax_deduction_basis == "Net Total":
			amount = self.doc.base_net_total

		elif category.tax_deduction_basis == "Gross Total":
			amount = self.doc.base_grand_total
			# deduct tax_withholding row
			for row in self.doc.taxes:
				if row.is_tax_withholding_account:
					amount = flt(
						amount - row.base_tax_amount_after_discount_amount,
						self.doc.precision("base_grand_total"),
					)

		category["taxable_amount"] += amount

	def update_taxable_value_based_on_item(self):
		for item in self.doc.get("items"):
			if not item.apply_tds:
				continue

			category = self.category_details.get(item.tax_withholding_category)
			amount = self._get_item_taxable_amount(item, category)
			category["taxable_amount"] = flt(
				category["taxable_amount"] + amount, self.doc.precision("base_net_total")
			)

	def is_doc_level_calculation(self):
		return len(self.category_details.keys()) == 1 and all(
			item.apply_tds for item in self.doc.get("items")
		)

	def _get_item_taxable_amount(self, item, category):
		if category.tax_deduction_basis == "Net Total":
			return item.base_net_amount

		return self._get_item_gross_amount(item)

	def _get_item_gross_amount(self, item):
		tax_amount = 0
		precision = self.doc.precision("tax_amount_after_discount_amount", "taxes")

		for tax_row in self.doc.taxes:
			if tax_row.is_tax_withholding_account or not tax_row.base_tax_amount_after_discount_amount:
				continue

			charge_type = tax_row.charge_type
			if tax_row.item_wise_tax_detail:
				item_tax_details = self.get_tax_details(tax_row).get(item.item_code or item.name, {})
				if not item_tax_details:
					continue

				tax_rate = self.get_item_tax_rate(item, tax_row)
				total_tax_amount = item_tax_details.get("tax_amount", 0.0)

				# Actual
				if not tax_rate and total_tax_amount:
					tax_amount += flt(item.net_amount * total_tax_amount / self.doc.net_total, precision)
					continue

				tax_amount += flt(self.get_item_tax_amount(item, tax_rate, charge_type), precision)

			elif charge_type == "Actual":
				tax_amount += flt(
					(item.net_amount * tax_row.base_tax_amount_after_discount_amount / self.doc.net_total),
					precision,
				)

		return flt(item.base_net_amount + tax_amount, self.doc.precision("base_net_amount", item))

	def get_tax_details(self, tax_row):
		if not getattr(tax_row, "__tax_details", None):
			tax_row.__tax_details = frappe.parse_json(tax_row.get("item_wise_tax_detail") or "{}")

		return tax_row.__tax_details

	def get_item_tax_rate(self, item, tax_row):
		item_tax_rates = frappe.parse_json(item.item_tax_rate)

		if tax_row.account_head in item_tax_rates:
			return item_tax_rates[tax_row.account_head]

		return tax_row.rate

	def get_item_tax_amount(self, item, tax_rate, charge_type):
		multiplier = item.qty if charge_type == "On Item Quantity" else item.base_net_amount / 100
		return tax_rate * multiplier

	def evaluate_thresholds(self):
		"""
		Evaluate if thresholds are crossed for each category

		All previous transactions are taxed immediately when either:
		- Single transaction threshold is crossed
		- Cumulative threshold is crossed
		"""
		# (by PAN)
		for category in self.category_details.values():
			category["threshold_crossed"] = False
			category["untilized_threshold"] = 0

			# threshold check skipped
			if self.doc.ignore_threshold_check or category.single_threshold == 0:
				category["threshold_crossed"] = True
				continue

			# single threshold
			if category.single_txn_threshold:
				category["threshold_crossed"] = category["taxable_amount"] >= category.single_txn_threshold
				continue

			# cumulative threshold
			if not category.tax_on_excess_amount:
				category["threshold_crossed"] = self._check_cumulative_threshold(category)
				continue

			# tax on excess amount
			else:
				threshold_data = self._check_untilized_threshold(category)
				category["threshold_crossed"] = threshold_data["threshold_crossed"]
				category["untilized_threshold"] = threshold_data["untilized_threshold"]

	def _check_cumulative_threshold(self, category):
		"""Check if cumulative threshold is crossed based on previous tax withheld"""
		# This would check if tax has been withheld previously for this party and category
		# TODO: Implement actual check based on business logic
		total_taxable_amount = self._get_historical_taxable_amount(category)
		return total_taxable_amount >= category.cumulative_threshold

	def _check_untilized_threshold(self, category):
		"""Check unutilized threshold for tax on excess amount"""
		# Calculate utilized threshold from historical data
		utilized_threshold = self._get_historical_withholding_amount(category)
		untilized_threshold = max(0, category.single_threshold - utilized_threshold)

		return {
			"threshold_crossed": True,  # Always calculate tax, but might be on reduced amount
			"untilized_threshold": untilized_threshold,
		}

	def get_short_excess_entries(self, category):
		"""Get historical tax withholding entries for processing"""
		entries = frappe.get_all(
			DOCTYPE,
			filters={
				"tax_withholding_category": category.name,
				"party_type": self.party_type,
				"party": self.party,
				"status": "Open",
				# Add date filters if needed
				# TODO: convert this to frappe.qb filter `taxable_date` is short deduction and `withholding_date` otherwise
				"withholding_date": ["between", [category.from_date, category.to_date]],
			},
			fields="*",
		)

		linked_payments = self._get_linked_payments()

		# Current + Short (old) / Advance + Excess (old)
		open_entries = {"short_deduction": deque(), "excess_deduction": deque()}

		for entry in entries:
			if entry.is_short_deduction:
				open_entries["short_deduction"].append(entry)
				continue

			if (entry.withholding_doctype, entry.withholding_name) in linked_payments:
				# TODO: only add proportionate amount
				open_entries["excess_deduction"].appendleft(entry)
				continue

			# Skip for manual adjustment
			# TODO: alternatively, also check allocation status of the linked payment
			if entry.withholding_doctype in ["Payment Entry", "Journal Entry"]:
				continue

			open_entries["excess_deduction"].append(entry)

		# Add current entry to short
		open_entries["short_deduction"].appendleft(
			frappe._dict(
				{
					"taxable_doctype": self.doc.doctype,
					"taxable_name": self.doc.name,
					"taxable_date": self.doc.posting_date,
					"taxable_amount": category.taxable_amount,
				}
			)
		)

		return open_entries

	def _get_linked_payments(self):
		"""Get payments linked to the current document"""
		# TODO: Implement actual fetch of linked payments
		# This should return a list of tuples (doctype, docname) for linked payments
		return [("Payment Entry", "PE-0001")]

	def _create_default_entry(self, category):
		"""Create a default entry template for the given category"""
		return {
			"party_type": self.party_type,
			"party": self.party,
			"tax_withholding_category": category.name,
			"tax_rate": category.tax_rate,
			"conversion_rate": self.doc.conversion_rate,
			"withholding_doctype": self.doc.doctype,
			"withholding_name": self.doc.name,
			"withholding_date": self.doc.posting_date,
			"withholding_amount": 0,  # Will be computed later
		}

	def _process_below_threshold_entry(self, category, default_entry):
		"""Process entry when threshold is not crossed"""
		entry = {**default_entry}

		if category.tax_on_excess_amount:
			# Add taxable information for excess tax
			entry.update(
				{
					"taxable_doctype": self.doc.doctype,
					"taxable_name": self.doc.name,
					"taxable_date": self.doc.posting_date,
					"taxable_amount": category.taxable_amount,
					"is_short_deduction": 1,
					"under_withheld_reason": "Tax on Excess",
				}
			)

		else:
			# Mark as short deduction
			entry.update(
				{
					"is_short_deduction": 1,
					"taxable_amount": category.taxable_amount,
				}
			)

		category.taxable_amount = 0

		return entry

	def _process_excess_threshold_entry(self, category, default_entry):
		"""Process entry for tax on excess amount"""
		entry = {**default_entry}

		taxable_amount = min(category.untilized_threshold, category.taxable_amount)

		entry.update(
			{
				"taxable_doctype": self.doc.doctype,
				"taxable_name": self.doc.name,
				"taxable_date": self.doc.posting_date,
				"taxable_amount": taxable_amount,
				"withholding_amount": 0,
				"is_short_deduction": 1,
				"under_withheld_reason": "Tax on Excess",
			}
		)

		# Reduce the remaining taxable amount
		category.taxable_amount -= taxable_amount

		return entry

	def _update_tax_rows(self):
		"""Update tax rows in the parent document"""
		pass

	def _merge_entries(
		self,
		short_entries: deque,
		excess_entries: deque,
		category,
		tax_rate=None,
		constraint=inf,
		default_obj=None,
	):
		"""
		Merge short and excess entries based on the tax rate and constraint.
		"""
		merged_entries = []

		if not short_entries or not excess_entries or constraint <= 0:
			return merged_entries

		if tax_rate is None:
			tax_rate = category.tax_rate

		def default_entry(short):
			entry = {}
			if default_obj:
				entry.update(default_obj)

			entry.update(
				{
					"taxable_doctype": short.taxable_doctype,
					"taxable_name": short.taxable_name,
					"taxable_date": short.taxable_date,
					"tax_withholding_category": category.name,
					"tax_rate": tax_rate,
					"party_type": self.party_type,
					"party": self.party,
				}
			)

			return entry

		# short and excess entries both available
		while short_entries and excess_entries and constraint > 0:
			if tax_rate == 0:
				break

			short = short_entries[0]
			excess = excess_entries[0]

			# Calculate the amount to merge
			amount_to_merge = min(short.taxable_amount, excess.withholding_amount / tax_rate, constraint)

			if amount_to_merge <= 0:
				break

			# Create a new merged entry
			merged_entry = {
				**default_entry(short),
				"taxable_amount": amount_to_merge,
				"withholding_amount": amount_to_merge * tax_rate / 100,  # TODO: Rounding settings
				"withholding_doctype": excess.withholding_doctype,
				"withholding_name": excess.withholding_name,
				"withholding_date": excess.withholding_date,
			}

			merged_entries.append(merged_entry)

			constraint -= amount_to_merge
			short.taxable_amount -= amount_to_merge
			excess.withholding_amount -= amount_to_merge * tax_rate / 100

			# Remove zero or negative value entries
			if short.taxable_amount <= 0:
				short_entries.popleft()

			if excess.withholding_amount <= 0:
				excess_entries.popleft()

		# Remaining short entries
		while short_entries and constraint > 0:
			short = short_entries[0]
			taxable_amount = min(short.taxable_amount, constraint)

			if taxable_amount <= 0:
				break

			merged_entry = {
				**default_entry(short),
				"taxable_amount": taxable_amount,
				"withholding_amount": taxable_amount * tax_rate / 100,  # TODO: Rounding settings
			}

			merged_entries.append(merged_entry)

			constraint -= taxable_amount
			short.taxable_amount -= taxable_amount

			if short.taxable_amount <= 0:
				short_entries.popleft()

		return merged_entries
