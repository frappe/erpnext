import frappe
from frappe.utils import flt

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

		returned_share = self.get_returned_share(original)
		for tax in charges:
			if same_charges := original_charges.get((tax.account_head, tax.description)):
				base_share = flt(same_charges.pop(0).base_tax_amount) * returned_share
				tax.tax_amount = -flt(base_share / doc.conversion_rate, tax.precision("tax_amount"))

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

	def get_returned_share(self, original) -> float:
		"""Part of a valuation charge of the original that the returned stock carried."""
		returned_qty = self.get_returned_qty_by_original_row()
		share = 0.0
		for row, proportion in get_charge_proportions(original):
			# a row carries its charge on its accepted qty, or on its rejected qty if it accepts nothing
			qty = returned_qty.get(row.name, {"accepted": 0.0, "rejected": 0.0})
			if flt(row.qty):
				carried_qty, returned = get_stock_qty(row, row.qty), qty["accepted"]
			else:
				carried_qty, returned = get_stock_qty(row, row.rejected_qty), qty["rejected"]

			if carried_qty:
				share += proportion * returned / carried_qty

		return share


def get_charge_proportions(doc) -> list:
	"""Part of a valuation charge each stock row takes, as update_valuation_rate spreads it."""
	stock_items = doc.get_stock_items() + doc.get_asset_items()
	items = [row for row in doc.get("items") if row.item_code in stock_items]

	total_qty = sum(flt(row.qty) for row in items)
	if total_qty:
		total_amount = sum(flt(row.base_net_amount) for row in items)
		return [
			(row, flt(row.base_net_amount) / total_amount if total_amount else flt(row.qty) / total_qty)
			for row in items
		]

	total_rejected_qty = sum(flt(row.get("rejected_qty")) for row in items)
	if total_rejected_qty and frappe.db.get_single_value(
		"Buying Settings", "set_valuation_rate_for_rejected_materials"
	):
		return [(row, flt(row.get("rejected_qty")) / total_rejected_qty) for row in items]

	return []


def get_actual_valuation_charges(doc) -> list:
	return [
		tax
		for tax in doc.get("taxes")
		if tax.charge_type == "Actual" and tax.category in ("Valuation", "Valuation and Total")
	]
