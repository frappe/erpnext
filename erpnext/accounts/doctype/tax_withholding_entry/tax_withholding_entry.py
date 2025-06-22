# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.model.document import Document

# TODO: Should threshold check be reduced with purchase returns?


class TaxWithholdingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		exchange_rate: DF.Float
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

	amount_to_adjust = entry.get(amount_field) * entry.exchange_rate

	if not amount_to_adjust or not old_entries:
		return

	for old_entry in old_entries:
		old_entry: TaxWithholdingEntry = frappe.get_doc("Tax Withholding Entry", **old_entry)

		old_used_amount = old_entry.get(used_field)
		old_exchange_rate = old_entry.exchange_rate

		if not for_cancel:
			# use unused amounts
			unused_amount = (old_entry.get(amount_field) - old_used_amount) * old_exchange_rate
			adj_amount = min(unused_amount, amount_to_adjust)
			new_used_amount = old_used_amount + adj_amount / old_exchange_rate

		else:
			# reduce already used amounts
			used_amount = old_used_amount * old_exchange_rate
			adj_amount = min(used_amount, amount_to_adjust)
			new_used_amount = old_used_amount - adj_amount / old_exchange_rate

		status = old_entry.get_status()
		frappe.db.set_value(
			"Tax Withholding Entry", old_entry.name, {used_field: new_used_amount, "status": status}
		)

		amount_to_adjust -= adj_amount
		if amount_to_adjust <= 0:
			break


# TODO: Only one date field

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

	def _get_category_details(self):
		category_names = set(
			item.tax_withholding_category
			for item in self.doc.items
			if item.tax_withholding_category and item.apply_tds
		)
		if self.doc.tax_withholding_category:
			category_names.add(self.doc.tax_withholding_category)

		return get_tax_withholding_categories(
			category_names, self.doc.posting_date, "Supplier", self.doc.supplier, self.doc.company
		)

	def calculate(self):
		self.category_details = self._get_category_details()
		self.set_category_wise_taxable_amount()
		self.evaluate_thresholds()

		entries = []
		for category in self.category_details.values():
			default_entry = {
				"party_type": "Supplier",
				"party": self.doc.supplier,
				"tax_withholding_category": category.name,
				"tax_rate": category.tax_rate,
				"exchange_rate": self.doc.exchange_rate,
				"source_doctype": self.doc.doctype,
				"source_name": self.doc.name,
				"source_date": self.doc.posting_date,
				"tax_withheld": 0,  # TODO: Computed Value
			}

			if not category.threshold_crossed:
				# TODO: add target information
				entry = {**default_entry}

				if category.tax_on_excess_amount:
					# Add target information
					entry.update(
						{
							"target_doctype": self.doc.doctype,
							"target_name": self.doc.name,
							"taxable_amount": category.taxable_amount,
						}
					)

				else:
					entry.update(
						{
							"is_short_deduction": 1,
							"taxable_amount": category.taxable_amount,
						}
					)

				entries.append(entry)
				continue

			# only for tax on excess amount
			if category.untilized_threshold:
				entry = {**default_entry}

				taxable_amount = min(
					category.untilized_threshold / self.doc.exchange_rate, category.taxable_amount
				)

				entry.update(
					{
						"target_doctype": self.doc.doctype,
						"target_name": self.doc.name,
						"taxable_amount": category.taxable_amount,
						"tax_withheld": 0,
						"is_short_deduction": 1,
						"short_deduction_reason": "Tax on Excess",
					}
				)

				category.taxable_amount -= taxable_amount

				if category.taxable_amount <= 0:
					continue

				# continue for balance

			historical_entries = self.get_historical_entries(category, "Supplier", self.doc.supplier)

			if category.ldc_unutilized_amount:
				for short in historical_entries["short_deduction"]:
					if not short.taxable_amount:
						continue

					# TODO: if is_not_valid_certificate:
					# should be ideally based on source date / document date
					# so, already filtered ldc should come here
					# continue

					if category.ldc_rate:
						for excess in historical_entries["excess_deduction"]:
							if not excess.tax_withheld:
								continue

							taxable_amount = (
								min(
									short.taxable_amount * short.exchange_rate,
									excess.tax_withheld * excess.exchange_rate / category.ldc_rate,
									category.ldc_unutilized_amount,
								)
								/ self.doc.exchange_rate
							)

							entry = {**default_entry}
							entry.update(
								{
									"target_doctype": short.target_doctype,
									"target_name": short.target_name,
									"target_date": short.target_date,
									"taxable_amount": taxable_amount,
									"rate": category.ldc_rate,
									"is_short_deduction": 1,
									"short_deduction_reason": "Lower Deduction Certificate",
									"lower_deduction_certificate": category.ldc_certificate,
								}
							)

							category.ldc_unutilized_amount -= taxable_amount * self.doc.exchange_rate
							short.taxable_amount -= taxable_amount
							excess.tax_withheld -= taxable_amount * category.ldc_rate / 100

							if (
								short.taxable_amount <= 0
								or category.ldc_unutilized_amount <= 0
								or excess.tax_withheld <= 0
							):
								break

					if not short.taxable_amount:
						continue

					taxable_amount = (
						min(short.taxable_amount * short.exchange_rate, category.ldc_unutilized_amount)
						/ self.doc.exchange_rate
					)
					entry = {**default_entry}

					entry.update(
						{
							"target_doctype": short.target_doctype,
							"target_name": short.target_name,
							"target_date": short.target_date,
							"taxable_amount": taxable_amount,
							"rate": category.ldc_rate,
							"is_short_deduction": 1,
							"short_deduction_reason": "Lower Deduction Certificate",
							"lower_deduction_certificate": category.ldc_certificate,
						}
					)

					category.ldc_unutilized_amount -= taxable_amount * self.doc.exchange_rate
					short.taxable_amount -= taxable_amount

					if short.taxable_amount <= 0 or category.ldc_unutilized_amount <= 0:
						break

				# TODO: update tax rate and tax amount
				pass

			# Process Old Open Entries
			for short in historical_entries["short_deduction"]:
				if not short.taxable_amount:
					continue

				for excess in historical_entries["excess_deduction"]:
					if not excess.tax_withheld:
						continue

					# TODO: LDC amount in Min
					taxable_amount = (
						min(
							short.taxable_amount * short.exchange_rate,
							excess.tax_withheld * excess.exchange_rate / excess.tax_rate,
						)
						/ self.doc.exchange_rate
					)

					# TODO: Update
					entry = {}
					entry["target_doctype"] = short.target_doctype
					entry["target_name"] = short.target_name
					entry["source_doctype"] = excess.source_doctype
					entry["source_name"] = excess.source_name
					entry["taxable_amount"] = taxable_amount
					entry["tax_withholding_category"] = category.name
					entry["tax_rate"] = category.tax_rate
					entry["tax_withheld"] = (
						taxable_amount * category.tax_rate / 100
					)  # TODO: Rounding settings

					short.taxable_amount -= taxable_amount
					excess.tax_withheld -= taxable_amount * category.tax_rate / 100

					if excess.tax_withheld <= 0 or short.taxable_amount <= 0:
						break

				if not short.taxable_amount:
					continue

				# TODO: Update short entries
				taxable_amount = short.taxable_amount * short.exchange_rate / self.doc.exchange_rate
				entry = {}
				entry["target_doctype"] = short.target_doctype
				entry["target_name"] = short.target_name
				entry["taxable_amount"] = taxable_amount
				entry["tax_withholding_category"] = category.name
				entry["tax_rate"] = category.tax_rate
				entry["tax_withheld"] = taxable_amount * category.tax_rate / 100  # TODO: Rounding

				# etc
				short.taxable_amount -= taxable_amount

				if short.taxable_amount <= 0:
					break

			for excess in historical_entries["excess_deduction"]:
				if not excess.tax_withheld:
					continue

				taxable_amount = (
					min(
						category.taxable_amount * self.doc.exchange_rate,
						excess.tax_withheld * excess.exchange_rate / excess.tax_rate,
					)
					/ self.doc.exchange_rate
				)

				entry = {}
				entry["target_doctype"] = self.doc.target_doctype
				entry["target_name"] = self.doc.target_name
				entry["source_doctype"] = excess.source_doctype
				entry["source_name"] = excess.source_name
				entry["taxable_amount"] = taxable_amount
				entry["tax_withholding_category"] = category.name
				entry["tax_rate"] = category.tax_rate
				entry["tax_withheld"] = taxable_amount * category.tax_rate / 100  # TODO: Rounding settings

				category.taxable_amount -= taxable_amount
				excess.tax_withheld -= taxable_amount * category.tax_rate / 100

				if excess.tax_withheld <= 0:
					break

			taxable_amount = category.taxable_amount
			entry["target_doctype"] = self.doc.doctype
			entry["target_name"] = self.doc.name
			entry["source_doctype"] = self.doc.doctype
			entry["source_name"] = self.doc.name
			entry["taxable_amount"] = taxable_amount
			entry["tax_withholding_category"] = category.name
			entry["tax_rate"] = category.tax_rate
			entry["tax_withheld"] = taxable_amount * category.tax_rate / 100  # TODO: Rounding settings

			# Add information with tax amount
			entries.append(
				{
					"category": category.name,
					"taxable_amount": category.taxable_amount,
					"tax_withheld": category.tax_withheld,
					"untilized_threshold": category.untilized_threshold,
				}
			)

		# TODO: add tax rows

	def set_category_wise_taxable_amount(self):
		# TODO: before exchange rate
		item_amount_map = frappe._dict(
			item_code={
				"net_amount": 100,
				"gross_amount": 120,
				"tax_withholding_category": "TDS Category",
			}
		)

		for item in item_amount_map.values():
			category_detail = self.category_details.get(item["tax_withholding_category"])

			if category_detail.tax_deduction_basis == "Net Total":
				category_detail["taxable_amount"] += item["net_amount"]
			else:
				category_detail["taxable_amount"] += item["gross_amount"]

	def evaluate_thresholds(self):
		for category in self.category_details.values():
			if self.doc.ignore_threshold_check or category.single_threshold == 0:
				category["threshold_crossed"] = True
				continue

			elif category.single_txn_threshold or category.single_threshold:
				category["threshold_crossed"] = category["taxable_amount"] >= category.single_threshold

			# Cumulative threshold
			# NOTE: By Pan
			elif not category.tax_on_excess_amount:
				# category["threshold_crossed"] = has_tax_been_withheld()
				pass

			# Tax on excess amount
			else:
				# category["threshold_crossed"] = get_untilized_threshold()
				# category["untilized_threshold"] = category.single_threshold - category.tax_withheld
				pass

	def get_historical_entries(self, category, party_type, party):
		# NOTE: By Party

		entries = frappe.get_all(
			"Tax Withholding Entry",
			filters={
				"tax_withholding_category": category.name,
				"party_type": party_type,
				"party": party,
				"status": "Open",
				# TODO: from and to dates filter from category
			},
			fields="*",
		)

		linked_payments = [("Payment Entry", "PE-0001")]

		result = defaultdict(defaultdict(dict))
		paid_through_payments = []
		for entry in entries:
			if entry.is_short_deduction:
				result["short_deduction"][(entry.target_doctype, entry.target_name)] = entry
				continue

			# Excess deduction
			if (entry.source_doctype, entry.source_name) in linked_payments:
				paid_through_payments.append(entry)
				continue

			# Manual Adjustment Required
			if entry.source_doctype in ["Payment Entry", "Journal Entry"]:
				continue

			# Adjusted on FIFO basis
			result["excess_deduction"][(entry.source_doctype, entry.source_name)] = entry

		return result, paid_through_payments
