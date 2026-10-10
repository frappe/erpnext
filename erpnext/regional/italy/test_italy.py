import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.regional.italy.utils import get_invoice_summary

VAT_7 = "_Test Italy VAT 7 - _TC"
VAT_19 = "_Test Italy VAT 19 - _TC"


def make_item(item_code, net_amount, tax_amount, item_tax_rate):
	return frappe._dict(
		item_code=item_code,
		net_amount=net_amount,
		tax_amount=tax_amount,
		item_tax_rate=item_tax_rate,
	)


def make_tax(account_head, total, charge_type="On Net Total", **kwargs):
	return frappe._dict(
		charge_type=charge_type,
		account_head=account_head,
		rate=0,
		total=total,
		tax_exemption_reason="N4-esenti",
		tax_exemption_law="Art.10",
		**kwargs,
	)


class TestItalyInvoiceSummary(FrappeTestCase):
	def test_not_applicable_tax_excluded_from_summary(self):
		"""An item that marks a tax not applicable belongs to another summary
		block. Counting it here inflates DatiRiepilogo and emits a block with
		AliquotaIVA 0.00 and no Natura, which SDI rejects."""
		items = [
			make_item("A", 100.0, 7.0, {VAT_7: 7.0, VAT_19: "N/A"}),
			make_item("B", 100.0, 19.0, {VAT_7: "N/A", VAT_19: 19.0}),
		]
		taxes = [make_tax(VAT_7, 107.0), make_tax(VAT_19, 126.0)]

		summary = get_invoice_summary(items, taxes)

		self.assertEqual(sorted(summary.keys()), ["19.0", "7.0"])
		self.assertEqual(summary["7.0"]["taxable_amount"], 100.0)
		self.assertEqual(summary["19.0"]["taxable_amount"], 100.0)

	def test_zero_rated_tax_keeps_exemption_reason(self):
		"""A genuine 0% rate is still exempt and must carry its Natura."""
		items = [make_item("C", 100.0, 0.0, {VAT_7: 0.0})]

		summary = get_invoice_summary(items, [make_tax(VAT_7, 100.0)])

		self.assertEqual(list(summary.keys()), ["0.0"])
		self.assertEqual(summary["0.0"]["taxable_amount"], 100.0)
		self.assertEqual(summary["0.0"]["tax_exemption_reason"], "N4-esenti")

	def test_all_items_not_applicable_falls_back_to_zero_vat(self):
		"""With every item excluded the summary would be empty, so the existing
		zero VAT fallback has to supply the block and its Natura."""
		items = [make_item("D", 100.0, 0.0, {VAT_7: "N/A"})]

		summary = get_invoice_summary(items, [make_tax(VAT_7, 100.0)])

		self.assertEqual(list(summary.keys()), ["0.0"])
		self.assertEqual(summary["0.0"]["tax_exemption_reason"], "N4-esenti")

	def test_previous_row_tax_with_only_not_applicable_items(self):
		"""The summary key leaks out of the item loop and is read again for
		previous-row charges. Every item being excluded leaves it unset."""
		items = [make_item("A", 100.0, 0.0, {VAT_7: 0.0, VAT_19: "N/A"})]
		taxes = [
			make_tax(VAT_7, 100.0, idx=1),
			make_tax(VAT_19, 100.0, charge_type="On Previous Row Total", idx=2, row_id=None),
		]

		summary = get_invoice_summary(items, taxes)

		self.assertEqual(list(summary.keys()), ["0.0"])
		self.assertEqual(summary["0.0"]["taxable_amount"], 100.0)
