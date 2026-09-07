# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.mapper import map_docs

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestMappedDiscounts(ERPNextTestSuite):
	def setUp(self):
		self.enterContext(
			self.change_settings("Buying Settings", maintain_same_rate=1, maintain_same_rate_action="Stop")
		)
		self.enterContext(self.change_settings("Stock Settings", auto_insert_price_list_rate_if_missing=0))

	def test_inclusive_taxes_and_full_discounts(self):
		for apply_discount_on in ("Net Total", "Grand Total"):
			for percentage in (10, 100):
				for inclusive in (False, True):
					with self.subTest(basis=apply_discount_on, percentage=percentage, inclusive=inclusive):
						rate = 110 if inclusive else 100
						discounted = self.make_order(
							rate=rate,
							percentage=percentage,
							inclusive=inclusive,
							apply_discount_on=apply_discount_on,
						)
						regular = self.make_order(item="_Test Item 2", rate=rate, inclusive=inclusive)
						for sources in ((discounted, regular), (regular, discounted)):
							receipt = self.combine(*sources).save()
							self.assertEqual(
								receipt.grand_total, discounted.grand_total + regular.grand_total
							)
							self.assertEqual(receipt.discount_amount, 0)
							items = {item.purchase_order: item for item in receipt.items}
							self.assertEqual(items[discounted.name].rate, rate)
							self.assertEqual(items[discounted.name].net_amount, discounted.net_total)
							self.assertEqual(items[regular.name].net_amount, regular.net_total)
							receipt.reload().save()
							self.assertEqual(
								receipt.grand_total, discounted.grand_total + regular.grand_total
							)

	def test_fixed_discount_consumption_survives_partial_mixed_receipts(self):
		for inclusive in (False, True):
			for discounted_first in (False, True):
				with self.subTest(inclusive=inclusive, discounted_first=discounted_first):
					rate = 110 if inclusive else 100
					discounted = self.make_order(
						qty=10, rate=rate, fixed=100, inclusive=inclusive, apply_discount_on="Grand Total"
					)
					regular = self.make_order(item="_Test Item 2", qty=5, rate=rate, inclusive=inclusive)
					sources = (discounted, regular) if discounted_first else (regular, discounted)
					first = self.combine(*sources)
					for item in first.items:
						if item.purchase_order == discounted.name:
							item.qty = 5
					first.save().submit()
					second = make_purchase_receipt(discounted.name).save()
					self.assertEqual(second.discount_amount, 50)
					self.assertEqual(
						first.grand_total + second.grand_total, discounted.grand_total + regular.grand_total
					)
					first.cancel()
					self.assertEqual(make_purchase_receipt(discounted.name).discount_amount, 100)

	def test_three_fixed_sources_keep_their_own_discounts(self):
		third_item = make_item("_Test Third Mapped Discount Item").name
		orders = [
			self.make_order(item=item, qty=10, fixed=discount)
			for item, discount in (("_Test Item", 100), ("_Test Item 2", 200), (third_item, 300))
		]
		for sources in (orders, list(reversed(orders))):
			receipt = self.combine(*sources).save()
			self.assertEqual(receipt.grand_total, 2400)
			items = {item.purchase_order: item for item in receipt.items}
			for source in sources:
				self.assertEqual(items[source.name].net_amount, source.net_total)
				self.assertEqual(items[source.name].rate, source.items[0].rate)
			receipt.items[0].rate -= 1
			with self.assertRaisesRegex(frappe.ValidationError, "Rate must be same"):
				receipt.save()

	def test_nonproportional_fixed_discount_remainder(self):
		discounted = self.make_order(qty=10, fixed=100)
		first = make_purchase_receipt(discounted.name)
		first.items[0].qty = 5
		first.discount_amount = 75
		first.save().submit()
		regular = self.make_order(item="_Test Item 2", qty=5)
		for sources in ((discounted, regular), (regular, discounted)):
			receipt = self.combine(*sources).save()
			items = {item.purchase_order: item for item in receipt.items}
			self.assertEqual(items[discounted.name].net_amount, 475)
			self.assertEqual(items[regular.name].net_amount, 500)
			self.assertEqual(receipt.grand_total, 975)

	def test_original_rate_validation_rejects_double_discount(self):
		discounted = self.make_order(percentage=10)
		receipt = make_purchase_receipt(discounted.name)
		receipt.items[0].price_list_rate = 100
		receipt.items[0].rate = 90
		with self.assertRaisesRegex(frappe.ValidationError, "Rate must be same"):
			receipt.save()

	def test_quantity_changed_before_adding_another_order(self):
		discounted = self.make_order(qty=10, percentage=10)
		regular = self.make_order(item="_Test Item 2", qty=5)
		receipt = make_purchase_receipt(discounted.name)
		receipt.items[0].qty = 5
		receipt = make_purchase_receipt(regular.name, receipt.as_dict()).save()
		self.assertEqual(receipt.items[0].net_amount, 450)
		self.assertEqual(receipt.grand_total, 950)

	def test_combined_receipt_discount_is_preserved_on_invoice(self):
		from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice

		discounted = self.make_order(percentage=10, rate=110, inclusive=True)
		regular = self.make_order(item="_Test Item 2", rate=110, inclusive=True)
		receipt = self.combine(discounted, regular).save().submit()
		invoice = make_purchase_invoice(receipt.name).save()
		self.assertEqual(invoice.grand_total, 209)
		self.assertEqual(invoice.items[0].rate, 110)
		self.assertEqual(invoice.items[0].net_amount, 90)

	def test_fixed_sales_discount_is_consumed_once_and_returned(self):
		from erpnext.accounts.doctype.sales_invoice.mapper import make_sales_return
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		with self.change_settings(
			"Selling Settings", maintain_same_sales_rate=1, maintain_same_rate_action="Stop"
		):
			discounted = make_sales_order(qty=10, rate=100, do_not_save=True)
			discounted.apply_discount_on = "Net Total"
			discounted.discount_amount = 100
			discounted.save().submit()
			regular = make_sales_order(item_code="_Test Item 2", qty=5, rate=100)
			invoice = map_docs(
				"erpnext.selling.doctype.sales_order.mapper.make_sales_invoice",
				[regular.name, discounted.name],
				frappe.new_doc("Sales Invoice").as_dict(),
			)
			invoice.items[1].qty = 5
			invoice.save().submit()
			self.assertEqual(invoice.grand_total, 950)
			remaining = make_sales_invoice(discounted.name).save()
			self.assertEqual(remaining.items[0].qty, 5)
			self.assertEqual(remaining.discount_amount, 50)
			self.assertEqual(remaining.grand_total, 450)
			credit_note = make_sales_return(invoice.name).save().submit()
			self.assertEqual(credit_note.grand_total, -950)
			self.assertEqual(credit_note.items[1].mapped_additional_discount_amount, 10)

	def make_order(
		self,
		*,
		item="_Test Item",
		qty=1,
		rate=100,
		percentage=0,
		fixed=0,
		inclusive=False,
		apply_discount_on="Net Total",
	):
		order = create_purchase_order(item_code=item, qty=qty, rate=rate, do_not_save=True)
		order.apply_discount_on = apply_discount_on
		order.additional_discount_percentage = percentage
		order.discount_amount = fixed
		if inclusive:
			order.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": "_Test Account VAT - _TC",
					"description": "VAT",
					"rate": 10,
					"included_in_print_rate": 1,
					"category": "Total",
					"add_deduct_tax": "Add",
				},
			)
		return order.save().submit()

	def combine(self, *sources):
		return map_docs(
			"erpnext.buying.doctype.purchase_order.mapper.make_purchase_receipt",
			[source.name for source in sources],
			frappe.new_doc("Purchase Receipt").as_dict(),
		)
