import frappe
from frappe.utils import flt


class ReturnChargesService:
	"""Actual valuation charges of a Purchase Receipt return."""

	def __init__(self, doc):
		self.doc = doc

	def set_returned_valuation_charges(self) -> None:
		"""Set each Actual valuation charge to the share the returned stock carried on the receipt."""
		doc = self.doc
		charges = [
			tax
			for tax in doc.get("taxes")
			if tax.charge_type == "Actual" and tax.category in ("Valuation", "Valuation and Total")
		]
		if not (doc.is_return and doc.return_against and charges):
			return

		receipt = frappe.get_doc(doc.doctype, doc.return_against)
		receipt_charges = {(tax.idx, tax.account_head): tax for tax in receipt.get("taxes")}
		returned_qty = self.get_returned_qty_by_receipt_row()
		for tax in charges:
			if receipt_charge := receipt_charges.get((tax.idx, tax.account_head)):
				share = self.get_returned_share(receipt, receipt_charge, returned_qty)
				tax.tax_amount = -flt(share, tax.precision("tax_amount"))

	def get_returned_qty_by_receipt_row(self) -> dict:
		"""Accepted and rejected qty returned, by receipt row."""
		returned_qty = {}
		for row in self.doc.get("items"):
			if row.return_qty_from_rejected_warehouse:
				accepted, rejected = 0.0, -flt(row.qty)
			else:
				accepted, rejected = -flt(row.qty), -flt(row.rejected_qty)

			qty = returned_qty.setdefault(row.purchase_receipt_item, {"accepted": 0.0, "rejected": 0.0})
			qty["accepted"] += accepted
			qty["rejected"] += rejected

		return returned_qty

	@staticmethod
	def get_returned_share(receipt, receipt_charge, returned_qty) -> float:
		items = [row for row in receipt.get("items") if row.item_code]
		if receipt_charge.get("allocate_full_amount_to_stock_items"):
			stock_items = receipt.get_stock_items() + receipt.get_asset_items()
			items = [row for row in items if row.item_code in stock_items]

		charge_per_item = {}
		receipt._spread_charge_over_items(charge_per_item, flt(receipt_charge.tax_amount), items)

		share = 0.0
		for row in items:
			# a row carries its charge on its accepted qty, or on its rejected qty if it accepts nothing
			carried_by = "accepted" if flt(row.qty) else "rejected"
			if carried_qty := flt(row.qty) or flt(row.rejected_qty):
				qty = returned_qty.get(row.name, {}).get(carried_by, 0.0)
				share += charge_per_item.get(row.idx, 0.0) * qty / carried_qty

		return share
