from collections import defaultdict

import frappe
from frappe.utils import flt

from erpnext.buying.doctype.buying_settings.buying_settings import bills_rejected_quantity
from erpnext.controllers.buying_controller import get_stock_qty
from erpnext.controllers.sales_and_purchase_return import (
	get_already_returned_items,
	get_return_against_item_fields,
)


class ReturnChargesService:
	"""Actual valuation charges of a return that moves stock back to the supplier."""

	def __init__(self, doc):
		self.doc = doc
		self.detail_field = get_return_against_item_fields(doc.doctype)

	def set_returned_valuation_charges(self) -> None:
		"""Set each Actual valuation charge to the share the returned stock carried on the original."""
		doc = self.doc
		charges = get_actual_valuation_charges(doc)
		if not (doc.is_return and doc.return_against and charges and self.is_traced_to_original()):
			return

		original = frappe.get_doc(doc.doctype, doc.return_against)
		original_charges = get_actual_valuation_charges(original)
		returned_qty = self.get_returned_qty_by_original_row()
		total_qty = add_returned_qty(self.get_earlier_returned_qty_by_original_row(), returned_qty)
		earlier_charges = self.get_earlier_returned_charges(original_charges)
		for tax, original_charge in pair_with_original_charges(charges, original_charges):
			tax.tax_amount = -self.get_returned_charge(
				original, original_charge, returned_qty, total_qty, earlier_charges[original_charge.name]
			)

	def get_returned_charge(
		self, original, original_charge, returned_qty, total_qty, earlier_base_charge
	) -> float:
		"""Rounded share of the charge that the returned stock carried.
		The return of the last stock that carried it takes the rest, so the returns add up to the charge."""
		precision = original_charge.precision("tax_amount")
		total_share = self.get_returned_base_share(original, original_charge, total_qty)
		if abs(flt(total_share, precision)) >= abs(flt(original_charge.base_tax_amount, precision)):
			base_share = original_charge.base_tax_amount + earlier_base_charge
		else:
			base_share = self.get_returned_base_share(original, original_charge, returned_qty)

		return flt(base_share / self.doc.conversion_rate, precision)

	def is_traced_to_original(self) -> bool:
		"""Only rows linked to the original row tell which charge the returned stock carried."""
		return all(row.get(self.detail_field) for row in self.doc.get("items"))

	def get_earlier_returned_qty_by_original_row(self) -> dict:
		"""Accepted and rejected stock qty of the other submitted returns, by original row."""
		return {
			row_name: {"accepted": flt(qty.stock_qty), "rejected": flt(qty.rejected_qty)}
			for (_item_code, row_name), qty in get_already_returned_items(self.doc).items()
		}

	def get_earlier_returned_charges(self, original_charges) -> defaultdict:
		"""Actual valuation charges of the other submitted returns in company currency, added up by the
		original charge they were mapped from."""
		earlier_returns = frappe.get_all(
			self.doc.doctype,
			filters={"docstatus": 1, "is_return": 1, "return_against": self.doc.return_against},
			pluck="name",
		)
		taxes_by_return = defaultdict(list)
		if earlier_returns:
			for tax in frappe.get_all(
				"Purchase Taxes and Charges",
				filters={
					"parenttype": self.doc.doctype,
					"parent": ["in", earlier_returns],
					"charge_type": "Actual",
					"category": ["in", ["Valuation", "Valuation and Total"]],
				},
				fields=["parent", "original_tax_row", "account_head", "description", "base_tax_amount"],
				order_by="idx",
			):
				taxes_by_return[tax.parent].append(tax)

		charges = defaultdict(float)
		for taxes in taxes_by_return.values():
			for tax, original_charge in pair_with_original_charges(taxes, original_charges):
				charges[original_charge.name] += flt(tax.base_tax_amount)

		return charges

	def get_returned_qty_by_original_row(self) -> dict:
		"""Accepted and rejected stock qty returned, by original row."""
		returned_qty = {}
		for row in self.doc.get("items"):
			if row.get("return_qty_from_rejected_warehouse"):
				accepted, rejected = 0.0, -get_stock_qty(row, row.qty)
			else:
				accepted, rejected = -get_stock_qty(row, row.qty), -get_stock_qty(row, row.rejected_qty)

			qty = returned_qty.setdefault(row.get(self.detail_field), {"accepted": 0.0, "rejected": 0.0})
			qty["accepted"] += accepted
			qty["rejected"] += rejected

		return returned_qty

	@staticmethod
	def get_returned_base_share(original, original_charge, returned_qty) -> float:
		"""Part of the charge, in company currency, that the returned stock carried."""
		items = [row for row in original.get("items") if row.item_code]
		if original_charge.get("allocate_full_amount_to_stock_items"):
			stock_items = original.get_stock_items() + original.get_asset_items()
			items = [row for row in items if row.item_code in stock_items]

		charge_per_item = {}
		original._spread_charge_over_items(charge_per_item, flt(original_charge.base_tax_amount), items)

		bills_rejected = bills_rejected_quantity(original)
		share = 0.0
		for row in items:
			# a row carries its charge on the stock its net amount paid for, or on its rejected qty if it accepts nothing
			qty = returned_qty.get(row.name, {"accepted": 0.0, "rejected": 0.0})
			if flt(row.qty):
				carried_qty = original.get_valued_stock_qty(row)
				returned = qty["accepted"] + (qty["rejected"] if bills_rejected else 0.0)
			else:
				carried_qty = get_stock_qty(row, row.rejected_qty)
				returned = qty["rejected"]

			if carried_qty:
				share += charge_per_item.get(row.idx, 0.0) * returned / carried_qty

		return share


def pair_with_original_charges(charges, original_charges) -> list:
	"""Each charge with the original charge it was mapped from, claimed by one charge only. Other charges,
	such as those of returns made before that link, take the next unclaimed original charge on the same
	account and description."""
	by_name = {tax.name: tax for tax in original_charges}
	claimed = {}
	for tax in charges:
		if tax.original_tax_row in by_name:
			claimed.setdefault(tax.original_tax_row, tax)

	unclaimed = {}
	for tax in original_charges:
		if tax.name not in claimed:
			unclaimed.setdefault((tax.account_head, tax.description), []).append(tax)

	pairs = []
	for tax in charges:
		if claimed.get(tax.original_tax_row) is tax:
			original_tax = by_name[tax.original_tax_row]
		else:
			same_charges = unclaimed.get((tax.account_head, tax.description))
			original_tax = same_charges.pop(0) if same_charges else None

		if original_tax:
			pairs.append((tax, original_tax))

	return pairs


def add_returned_qty(earlier_qty, returned_qty) -> dict:
	"""Accepted and rejected stock qty of both, by original row."""
	total_qty = defaultdict(lambda: {"accepted": 0.0, "rejected": 0.0})
	for qty_by_row in (earlier_qty, returned_qty):
		for row_name, qty in qty_by_row.items():
			total_qty[row_name]["accepted"] += qty["accepted"]
			total_qty[row_name]["rejected"] += qty["rejected"]

	return total_qty


def get_actual_valuation_charges(doc) -> list:
	return [
		tax
		for tax in doc.get("taxes")
		if tax.charge_type == "Actual" and tax.category in ("Valuation", "Valuation and Total")
	]
