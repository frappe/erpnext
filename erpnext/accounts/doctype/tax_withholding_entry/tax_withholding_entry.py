# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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
		short_deduction_reason: DF.Literal["", "Threshold not crossed", "Lower Deduction Certificate"]
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
		self.set_tax_witholding_flags()
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

	def set_tax_witholding_flags(self):
		if not self.source_name:
			self.is_short_deduction = 1
			self.tax_withheld = 0

		if not self.target_name:
			self.is_excess_deduction = 1
			self.taxable_amount = 0

	def set_status(self):
		"""Update the status of this entry based on its current state"""
		self.status = self.get_status()

	def get_status(self):
		"""Get the current status of this entry"""
		if self.docstatus == 2:
			return "Cancelled"

		if self.is_short_deduction:
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

	field_mapping = {
		"doctype_field": "source_doctype" if is_short else "target_doctype",
		"name_field": "source_name" if is_short else "target_name",
		"amount_field": "taxable_amount" if is_short else "tax_withheld",
	}
	field_mapping["used_field"] = f"used_{field_mapping['amount_field']}"

	status_filter = "Open" if not for_cancel else ["in", ["Open", "Closed"]]

	# filter
	filters = {
		"tax_withholding_category": entry.tax_withholding_category,
		field_mapping["doctype_field"]: getattr(entry, field_mapping["doctype_field"]),
		field_mapping["name_field"]: getattr(entry, field_mapping["name_field"]),
		f"is_{adjustment_type}": 1,
		"status": status_filter,
	}

	if is_short:
		# TODO: Tax on excess? ignore threshold check
		filters["short_deduction_reason"] = ["!=", "Lower Deduction Certificate"]

	entries = frappe.get_all("Tax Withholding Entry", filters=filters, fields="*")

	return {"entries": entries, "field_mapping": field_mapping}


def adjust_entry_amounts(entry, adjustment_type, for_cancel):
	"""
	Adjust tax withholding entries for both short deduction and excess deduction cases.
	This function coordinates the adjustment process using smaller focused functions.

	Args:
	        entry: The tax withholding entry document
	        adjustment_type: Either "short_deduction" or "excess_deduction"
	        for_cancel: True if this is for a cancel operation, False for submit
	"""
	operation_info = get_entries_to_adjust(entry, adjustment_type, for_cancel)

	old_entries = operation_info["entries"]
	field_mapping = operation_info["field_mapping"]
	amount_field = field_mapping["amount_field"]
	used_field = field_mapping["used_field"]

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
