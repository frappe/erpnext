# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict, deque
from math import inf

import frappe
from frappe.model.document import Document

# TODO: Should threshold check be reduced with purchase returns?


class TaxWithholdingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_rate: DF.Float
		currency: DF.Link | None
		is_excess_deduction: DF.Check
		is_manual_override: DF.Check
		is_short_deduction: DF.Check
		lower_deduction_certificate: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		short_deduction_reason: DF.Literal["", "Tax on Excess", "Lower Deduction Certificate"]
		source_date: DF.Date | None
		source_doctype: DF.Link | None
		source_name: DF.DynamicLink | None
		status: DF.Literal["", "Matched", "Open", "Closed", "Cancelled"]
		target_date: DF.Date | None
		target_doctype: DF.Link | None
		target_name: DF.DynamicLink | None
		tax_id: DF.Data | None
		tax_rate: DF.Percent
		tax_withheld: DF.Currency
		tax_withholding_category: DF.Link | None
		taxable_amount: DF.Currency
		used_tax_withheld: DF.Currency
		used_taxable_amount: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.set_tax_withholding_flags()
		self.set_status()

	def on_submit(self):
		self.adjust_linked_entries(for_cancel=False)

	def on_cancel(self):
		self.adjust_linked_entries(for_cancel=True)

	def adjust_linked_entries(self, for_cancel=False):
		"""
		Adjusts related entries.
		This method acts as a coordinator for the adjustment process.

		Args:
		        for_cancel: True if this is for a cancel operation, False for submit
		"""
		# Process short deduction adjustments if applicable
		if self.source_doctype != self.parenttype or self.source_name != self.parent:
			adjust_entry_amounts(self, "short_deduction", for_cancel)

		# Process excess deduction adjustments if applicable
		if self.target_doctype != self.parenttype or self.target_name != self.parent:
			adjust_entry_amounts(self, "excess_deduction", for_cancel)

	def set_tax_withholding_flags(self):
		if not self.source_name:
			self.is_short_deduction = 1
			self.tax_withheld = 0

		elif not self.target_name:
			self.is_excess_deduction = 1

			# Considered for threshold check
			if self.source_doctype != "Payment Entry":
				self.taxable_amount = 0

	def set_status(self):
		"""Update the status of this entry based on its current state"""
		self.status = self.get_status()

	def get_status(self):
		"""Get the current status of this entry"""
		if self.docstatus == 2:
			return "Cancelled"

		# Reasons are genuine allowed reasons for short deduction.
		# Hence if a reason is provided, consider it as matched.
		if self.is_short_deduction and not self.short_deduction_reason:
			return "Closed" if self.used_taxable_amount >= self.taxable_amount else "Open"

		elif self.is_excess_deduction:
			return "Closed" if self.used_tax_withheld >= self.tax_withheld else "Open"

		else:
			return "Matched"


def get_entries_to_adjust(entry, adjustment_type, for_cancel):
	"""
	Find entries that need adjustment based on the current entry and operation type.

	Args:
	        entry: The tax withholding entry document
	        adjustment_type: Either "short_deduction" or "excess_deduction"
	        for_cancel: True if this is for a cancel operation, False for submit

	Returns:
	        dict: Contains entry list, field mappings, and adjustment parameters
	"""
	is_short = adjustment_type == "short_deduction"

	field_map = {
		"doctype_field": "source_doctype" if is_short else "target_doctype",
		"name_field": "source_name" if is_short else "target_name",
		"amount_field": "taxable_amount" if is_short else "tax_withheld",
	}
	field_map["used_field"] = f"used_{field_map['amount_field']}"

	status_filter = "Open" if not for_cancel else ["in", ["Open", "Closed"]]

	# filter
	filters = {
		"tax_withholding_category": entry.tax_withholding_category,
		field_map["doctype_field"]: getattr(entry, field_map["doctype_field"]),
		field_map["name_field"]: getattr(entry, field_map["name_field"]),
		f"is_{adjustment_type}": 1,
		"status": status_filter,
	}

	if is_short:
		# TODO: Tax on excess? ignore threshold check
		filters["short_deduction_reason"] = ["!=", "Lower Deduction Certificate"]

	entries = frappe.get_all("Tax Withholding Entry", filters=filters, fields="*")

	return {
		"entries": entries,
		"amount_field": field_map["amount_field"],
		"used_field": field_map["used_field"],
	}


def adjust_entry_amounts(entry, adjustment_type, for_cancel):
	"""
	Adjust tax withholding entries for both short deduction and excess deduction cases.

	Args:
	        entry: The tax withholding entry document
	        adjustment_type: Either "short_deduction" or "excess_deduction"
	        for_cancel: True if this is for a cancel operation, False for submit
	"""
	operation_info = get_entries_to_adjust(entry, adjustment_type, for_cancel)

	old_entries = operation_info["entries"]
	amount_field = operation_info["amount_field"]
	used_field = operation_info["used_field"]

	amount_to_adjust = entry.get(amount_field)

	if not amount_to_adjust or not old_entries:
		return

	for old_entry in old_entries:
		old_entry: TaxWithholdingEntry = frappe.get_doc("Tax Withholding Entry", **old_entry)

		old_used_amount = old_entry.get(used_field)

		if not for_cancel:
			# use unused amounts
			unused_amount = old_entry.get(amount_field) - old_used_amount
			adj_amount = min(unused_amount, amount_to_adjust)
			new_used_amount = old_used_amount + adj_amount

		else:
			# reduce already used amounts
			used_amount = old_used_amount
			adj_amount = min(used_amount, amount_to_adjust)
			new_used_amount = old_used_amount - adj_amount

		status = old_entry.get_status()
		frappe.db.set_value(
			"Tax Withholding Entry", old_entry.name, {used_field: new_used_amount, "status": status}
		)

		amount_to_adjust -= adj_amount
		if amount_to_adjust <= 0:
			break


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
# -- Check for short deductions historically (ignore source doctype == payment entry)
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
					"short_deduction_reason": "Lower Deduction Certificate",
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
			if entry.get("source_name"):
				continue

			entry.update(
				source_doctype=self.doc.doctype,
				source_name=self.doc.name,
				source_date=self.doc.posting_date,
			)

		# Update tax rows in the parent document
		# TODO

	def set_category_wise_taxable_amount(self):
		# TODO
		return

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
		utilized_threshold = self._get_historical_tax_withheld(category)
		untilized_threshold = max(0, category.single_threshold - utilized_threshold)

		return {
			"threshold_crossed": True,  # Always calculate tax, but might be on reduced amount
			"untilized_threshold": untilized_threshold,
		}

	def get_short_excess_entries(self, category):
		"""Get historical tax withholding entries for processing"""
		entries = frappe.get_all(
			"Tax Withholding Entry",
			filters={
				"tax_withholding_category": category.name,
				"party_type": self.party_type,
				"party": self.party,
				"status": "Open",
				# Add date filters if needed
				# TODO: convert this to frappe.qb filter `target_date` is short deduction and `source_date` otherwise
				"source_date": ["between", [category.from_date, category.to_date]],
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

			if (entry.source_doctype, entry.source_name) in linked_payments:
				# TODO: only add proportionate amount
				open_entries["excess_deduction"].appendleft(entry)
				continue

			# Skip for manual adjustment
			# TODO: alternatively, also check allocation status of the linked payment
			if entry.source_doctype in ["Payment Entry", "Journal Entry"]:
				continue

			open_entries["excess_deduction"].append(entry)

		# Add current entry to short
		open_entries["short_deduction"].appendleft(
			frappe._dict(
				{
					"target_doctype": self.doc.doctype,
					"target_name": self.doc.name,
					"target_date": self.doc.posting_date,
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
			"source_doctype": self.doc.doctype,
			"source_name": self.doc.name,
			"source_date": self.doc.posting_date,
			"tax_withheld": 0,  # Will be computed later
		}

	def _process_below_threshold_entry(self, category, default_entry):
		"""Process entry when threshold is not crossed"""
		entry = {**default_entry}

		if category.tax_on_excess_amount:
			# Add target information for excess tax
			entry.update(
				{
					"target_doctype": self.doc.doctype,
					"target_name": self.doc.name,
					"target_date": self.doc.posting_date,
					"taxable_amount": category.taxable_amount,
					"is_short_deduction": 1,
					"short_deduction_reason": "Tax on Excess",
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
				"target_doctype": self.doc.doctype,
				"target_name": self.doc.name,
				"target_date": self.doc.posting_date,
				"taxable_amount": taxable_amount,
				"tax_withheld": 0,
				"is_short_deduction": 1,
				"short_deduction_reason": "Tax on Excess",
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
					"target_doctype": short.target_doctype,
					"target_name": short.target_name,
					"target_date": short.target_date,
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
			amount_to_merge = min(short.taxable_amount, excess.tax_withheld / tax_rate, constraint)

			if amount_to_merge <= 0:
				break

			# Create a new merged entry
			merged_entry = {
				**default_entry(short),
				"taxable_amount": amount_to_merge,
				"tax_withheld": amount_to_merge * tax_rate / 100,  # TODO: Rounding settings
				"source_doctype": excess.source_doctype,
				"source_name": excess.source_name,
				"source_date": excess.source_date,
			}

			merged_entries.append(merged_entry)

			constraint -= amount_to_merge
			short.taxable_amount -= amount_to_merge
			excess.tax_withheld -= amount_to_merge * tax_rate / 100

			# Remove zero or negative value entries
			if short.taxable_amount <= 0:
				short_entries.popleft()

			if excess.tax_withheld <= 0:
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
				"tax_withheld": taxable_amount * tax_rate / 100,  # TODO: Rounding settings
			}

			merged_entries.append(merged_entry)

			constraint -= taxable_amount
			short.taxable_amount -= taxable_amount

			if short.taxable_amount <= 0:
				short_entries.popleft()

		return merged_entries
