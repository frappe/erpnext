# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import deque
from math import inf

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt

import erpnext

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
		"""Update the status of this entry based on its current state"""
		if not status:
			status = self.get_status()

		self.status = status

	def get_status(self):
		"""Get the current status of this entry"""
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

	@property
	def is_taxable_different(self):
		return self.taxable_doctype != self.parenttype or self.taxable_name != self.parent

	@property
	def is_withholding_different(self):
		return self.withholding_doctype != self.parenttype or self.withholding_name != self.parent

	# SUBMIT

	def _process_tax_withholding_adjustments(self):
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

		# update
		for old_entry_data in old_entries:
			old_entry = frappe.get_doc(DOCTYPE, **old_entry_data)
			old_amount = abs(old_entry.get(amount_field))

			if old_entry.get(amount_field) * value_direction < 0:
				# sign of old entry's amount is different
				continue

			amount_we_can_match = min(old_amount, remaining_amount)
			proportion = amount_we_can_match / old_amount if old_amount else 0
			values_to_update = self._get_values_to_update(proportion, field_type)

			if old_amount <= amount_we_can_match:
				# complete adjustment
				frappe.db.set_value(DOCTYPE, old_entry.name, values_to_update)

			else:
				# partial adjustment
				balance_amount = (old_amount - amount_we_can_match) * value_direction
				frappe.db.set_value(DOCTYPE, old_entry.name, {amount_field: balance_amount})

				# new entry
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

		# NOTE: Allow offsetting across different categories
		# Update Tax Withholding Category values

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
					"docstatus": 1,
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
					"docstatus": 1,
				},
				{
					"taxable_name": "",
					"taxable_doctype": "",
					"taxable_amount": 0,
					"status": "Over Withheld",
				},
			)


def on_invoice_submit(doc):
	for entry in doc.tax_withholding_entries:
		entry: TaxWithholdingEntry
		entry._process_tax_withholding_adjustments()


def on_invoice_cancel(doc):
	for entry in doc.tax_withholding_entries:
		entry: TaxWithholdingEntry
		entry._clear_old_references()


def on_invoice_validate(doc):
	if not doc.apply_tds:
		doc.tax_withholding_entries = []
		doc.tax_withholding_category = None
		# TODO: remove tds row from taxes table

		return

	TaxWithholdingController(doc).calculate()

	for entry in doc.tax_withholding_entries:
		entry: TaxWithholdingEntry
		entry.set_status(entry.status)
		entry.validate_adjustments()


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
		TaxWithholdingAmount(self.doc, self.category_details).set_taxable_amount()

		# Step 3: Apply threshold rules
		self.evaluate_thresholds()

		# Step 4: Process each category
		for category in self.category_details.values():
			# threshold not crossed
			if not category.threshold_crossed:
				self.entries.append(
					{
						**self._create_default_entry(category),
						"taxable_amount": category.taxable_amount,
					}
				)
				category.taxable_amount = 0
				continue

			# tax on over amount
			elif category.unused_threshold:
				self.entries.append(self._process_excess_threshold_entry(category))

				if category.taxable_amount <= 0:
					continue

			open_entries = self.get_under_over_withheld_entries(category)

			# ldc
			if category.ldc_unutilized_amount:
				default_obj = {
					"under_withheld_reason": "Lower Deduction Certificate",
					"lower_deduction_certificate": category.ldc_certificate,
				}
				merged = self._merge_entries(
					open_entries["under_withheld"],
					open_entries["over_withheld"],
					category,
					tax_rate=category.ldc_rate,
					constraint=category.ldc_unutilized_amount,
					default_obj=default_obj,
				)

				self.entries.extend(merged)
				if not open_entries["under_withheld"]:
					continue

			# to pay
			merged = self._merge_entries(
				open_entries["under_withheld"], open_entries["over_withheld"], category
			)

			self.entries.extend(merged)

		# Step 5: Process entries for existing document
		if not any(entry.is_manual_override for entry in self.doc.tax_withholding_entries):
			self.doc.tax_withholding_entries = []
			self.doc.extend("tax_withholding_entries", self.entries)

		else:
			# TODO
			# To the extent of taxable amount with manual override
			# Reduce the entries to be processed above

			pass

		# TODO
		# Step 6: Update tax rows in the parent document

	def evaluate_thresholds(self):
		"""
		Evaluate if thresholds are crossed for each category

		All previous transactions are taxed immediately when either:
		- Single transaction threshold is crossed
		- Cumulative threshold is crossed
		"""
		# (by PAN)
		for category in self.category_details.values():
			category.threshold_crossed = False
			category.unused_threshold = 0

			# threshold check skipped
			if self.doc.ignore_tax_withholding_threshold:
				category.threshold_crossed = True

			# only transaction threshold
			elif category.disable_cumulative_threshold:
				category.threshold_crossed = category.taxable_amount >= category.single_threshold

			# no cumulative threshold
			elif category.cumulative_threshold == 0:
				category.threshold_crossed = True

			# cumulative / transaction threshold
			elif not category.tax_on_excess_amount:
				category.threshold_crossed = self._is_threshold_crossed(category)

			# tax on excess amount
			else:
				category.threshold_crossed = True
				category.unused_threshold = self._get_unused_threshold(category)

	def _is_threshold_crossed(self, category):
		"""Check if cumulative threshold is crossed based on previous tax withheld"""
		entry = frappe.qb.DocType(DOCTYPE)
		result = frappe._dict(
			self._base_threshold_query(category).where(entry.status.isin(["Settled", "Under Withheld"])).run()
		)

		# NOTE: Once deducted, always deducted. Not checking cumulative threshold again purposefully.
		# conservative approach to avoid tax disputes as it can have conflicting views
		# https://www.taxtmi.com/forum/issue?id=118627

		if result.get("Settled", 0) > 0:
			return True

		# Cumulative / Transaction Threshold Check
		threshold_to_check = category.cumulative_threshold - result.get("Under Withheld", 0)

		if not category.disable_transaction_threshold:
			threshold_to_check = min(threshold_to_check, category.single_threshold)

		return category.taxable_amount >= threshold_to_check

	def _get_unused_threshold(self, category):
		"""Check unutilized threshold for tax on excess amount"""
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
			.where(entry.tax_withholding_category == category.name)
			.where(entry.tax_withholding_group == self.doc.tax_withholding_group)
			.where(entry.docstatus == 1)
			.groupby(entry.status)
		)

		# NOTE: This can be a configurable option
		# To check if filter by tax_id is needed
		tax_id = get_tax_id(self.party_type, self.party)
		if tax_id:
			query = query.where(entry.tax_id == tax_id)

		else:
			query = query.where(entry.party_type == self.party_type).where(entry.party == self.party)

		return query

	def get_under_over_withheld_entries(self, category):
		"""Get historical tax withholding entries for processing"""

		entries = self._get_under_over_entries(category)
		linked_payments = self._get_linked_payments()

		# Current + Under Withheld (old) / Advance + Over Withheld (old)
		open_entries = {"under_withheld": deque(), "over_withheld": deque()}

		for entry in entries:
			if entry.status == "Under Withheld":
				open_entries["under_withheld"].append(entry)
				continue

			key = (entry.withholding_doctype, entry.withholding_name)
			if key in linked_payments:
				# allocated / allocable
				proportion = linked_payments[key] / (entry.taxable_amount - entry.withholding_amount)
				entry.withholding_amount = entry.withholding_amount * proportion
				open_entries["over_withheld"].appendleft(entry)
				continue

			# Skip for manual adjustment
			# TODO: alternatively, also check allocation status of the linked payment
			if entry.withholding_doctype in ["Payment Entry", "Journal Entry"]:
				continue

			open_entries["over_withheld"].append(entry)

		# Add current entry as under withheld
		open_entries["under_withheld"].appendleft(
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

	def _get_under_over_entries(self, category):
		# NOTE: Allow offsetting across different categories
		# Change Filters

		entry = frappe.qb.DocType(DOCTYPE)
		base_query = (
			frappe.qb.from_(entry)
			.select("*")
			.where(entry.tax_withholding_category == category.name)
			.where(entry.party_type == self.party_type)
			.where(entry.party == self.party)
			.where(entry.docstatus == 1)
		)

		over_withheld_query = base_query.where(entry.status == "Over Withheld").where(
			entry.withholding_date.between(category.from_date, category.to_date)
		)

		return (
			base_query.where(entry.status == "Under Withheld")
			.where(entry.taxable_date.between(category.from_date, category.to_date))
			.union(over_withheld_query)
			.run(as_dict=True)
		)

	def _get_linked_payments(self):
		"""Get payments linked to the current document"""
		references = frappe._dict()
		for ref in self.doc.advances:
			key = (ref.reference_doctype, ref.reference_name)
			references[key] = ref.allocated_amount * self.doc.conversion_rate

		return references

	def _create_default_entry(self, category):
		"""Create a default entry template for the given category"""
		return {
			"party_type": self.party_type,
			"party": self.party,
			"tax_withholding_category": category.name,
			"tax_withholding_group": category.tax_withholding_group,
			"tax_rate": category.tax_rate,
			"conversion_rate": self.doc.conversion_rate,
			"taxable_doctype": self.doc.doctype,
			"taxable_name": self.doc.name,
			"taxable_date": self.doc.posting_date,
			"taxable_amount": 0,
			"withholding_doctype": self.doc.doctype,
			"withholding_name": self.doc.name,
			"withholding_date": self.doc.posting_date,
			"withholding_amount": 0,  # Will be computed later
		}

	def _process_excess_threshold_entry(self, category):
		"""Process entry for tax on excess amount"""

		taxable_amount = min(category.unused_threshold, category.taxable_amount)

		# Reduce the remaining taxable amount
		category.taxable_amount -= taxable_amount

		return {
			**self._create_default_entry(category),
			"taxable_amount": taxable_amount,
			"under_withheld_reason": "Threshold Exemption",
		}

	def _update_tax_rows(self):
		"""Update tax rows in the parent document"""
		pass

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
		If only under entries are available, they will be processed against current document.
		"""
		merged_entries = []

		if not under_entries or constraint <= 0:
			return merged_entries

		if tax_rate is None:
			tax_rate = category.tax_rate

		def default_entry(under):
			entry = {}
			if default_obj:
				entry.update(default_obj)

			entry.update(
				{
					"taxable_doctype": under.taxable_doctype,
					"taxable_name": under.taxable_name,
					"taxable_date": under.taxable_date,
					"tax_withholding_category": category.name,
					"tax_rate": tax_rate,
					"party_type": self.party_type,
					"party": self.party,
				}
			)

			return entry

		# under and over entries both available
		while under_entries and over_entries and constraint > 0:
			if tax_rate == 0:
				break

			under = under_entries[0]
			over = over_entries[0]

			# Calculate the amount to merge
			amount_to_merge = min(under.taxable_amount, over.withholding_amount / tax_rate, constraint)

			if amount_to_merge <= 0:
				break

			# Create a new merged entry
			merged_entry = {
				**default_entry(under),
				"taxable_amount": amount_to_merge,
				"withholding_amount": amount_to_merge * tax_rate / 100,  # TODO: Rounding settings
				"withholding_doctype": over.withholding_doctype,
				"withholding_name": over.withholding_name,
				"withholding_date": over.withholding_date,
			}

			if merged_entry.taxable_name == self.doc.name or merged_entry.withholding_name == self.doc.name:
				merged_entries.append(merged_entry)

			constraint -= amount_to_merge
			under.taxable_amount -= amount_to_merge
			over.withholding_amount -= amount_to_merge * tax_rate / 100

			# Remove zero or negative value entries
			if under.taxable_amount <= 0:
				under_entries.popleft()

			if over.withholding_amount <= 0:
				over_entries.popleft()

		# Remaining under entries
		while under_entries and constraint > 0:
			under = under_entries[0]
			taxable_amount = min(under.taxable_amount, constraint)

			if taxable_amount <= 0:
				break

			merged_entry = {
				**default_entry(under),
				"taxable_amount": taxable_amount,
				"withholding_amount": taxable_amount * tax_rate / 100,  # TODO: Rounding settings
				# Paid from the current document
				"withholding_doctype": self.doc.doctype,
				"withholding_name": self.doc.name,
				"withholding_date": self.doc.posting_date,
			}

			merged_entries.append(merged_entry)

			constraint -= taxable_amount
			under.taxable_amount -= taxable_amount

			if under.taxable_amount <= 0:
				under_entries.popleft()

		return merged_entries


class TaxWithholdingAmount:
	def __init__(self, doc, category_details):
		self.doc = doc
		self.category_details = category_details

	def set_taxable_amount(self):
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


def _reset_idx(docs_to_reset_idx):
	updates = []
	for doctype, docname in docs_to_reset_idx:
		names = frappe.get_all(
			DOCTYPE,
			filters={"parent": docname, "parenttype": doctype, "docstatus": 1},
			pluck="name",
		)

		for idx, name in enumerate(names, start=1):
			updates.append({"name": name, "idx": idx})

	frappe.db.bulk_update(DOCTYPE, updates, update_modified=False)


@erpnext.allow_regional
def get_tax_id(party_type, party):
	return None
