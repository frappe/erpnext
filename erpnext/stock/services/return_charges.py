import frappe
from frappe.utils import flt

from erpnext.buying.doctype.buying_settings.buying_settings import bills_rejected_quantity
from erpnext.controllers.buying_controller import get_stock_qty
from erpnext.controllers.sales_and_purchase_return import get_return_against_item_fields


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
		# rows can be removed from a return, so match each charge to the original's by account and description
		original_charges = {}
		for tax in get_actual_valuation_charges(original):
			original_charges.setdefault((tax.account_head, tax.description), []).append(tax)

		returned_amounts = self.get_returned_charge_amounts(original)
		for tax in charges:
			if same_charges := original_charges.get((tax.account_head, tax.description)):
				tax.tax_amount = -returned_amounts[same_charges.pop(0).name]

	def get_returned_charge_amounts(self, original) -> dict:
		"""Part of each Actual valuation charge of the original that the returned stock carried, in the
		return's currency. The original spreads its charges together, so they share the part of their sum."""
		groups = {}
		for tax in get_actual_valuation_charges(original):
			groups.setdefault(bool(tax.get("allocate_full_amount_to_stock_items")), []).append(tax)

		returned_qty = self.get_returned_qty_by_original_row()
		amounts = {}
		for to_stock_items, taxes in groups.items():
			total = sum(flt(tax.base_tax_amount) for tax in taxes)
			if not total:
				continue

			precision = taxes[0].precision("tax_amount")
			base_share = self.get_returned_base_share(original, total, to_stock_items, returned_qty)
			share = flt(base_share / self.doc.conversion_rate, precision)
			for tax in taxes[:-1]:
				amounts[tax.name] = flt(share * flt(tax.base_tax_amount) / total, precision)
			amounts[taxes[-1].name] = flt(share - sum(amounts[tax.name] for tax in taxes[:-1]), precision)

		return amounts

	def is_traced_to_original(self) -> bool:
		"""Only rows linked to the original row tell which charge the returned stock carried."""
		return all(row.get(self.detail_field) for row in self.doc.get("items"))

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
	def get_returned_base_share(original, base_charge, to_stock_items, returned_qty) -> float:
		"""Part of the charge, in company currency, that the returned stock carried."""
		items = [row for row in original.get("items") if row.item_code]
		if to_stock_items:
			stock_items = original.get_stock_items() + original.get_asset_items()
			items = [row for row in items if row.item_code in stock_items]

		charge_per_item = {}
		original._spread_charge_over_items(charge_per_item, base_charge, items)

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


def get_actual_valuation_charges(doc) -> list:
	return [
		tax
		for tax in doc.get("taxes")
		if tax.charge_type == "Actual" and tax.category in ("Valuation", "Valuation and Total")
	]
