# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.mapper import map_docs
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite

PURCHASE_RECEIPT_FROM_ORDER = "erpnext.buying.doctype.purchase_order.mapper.make_purchase_receipt"
PURCHASE_INVOICE_FROM_ORDER = "erpnext.buying.doctype.purchase_order.mapper.make_purchase_invoice"
PURCHASE_INVOICE_FROM_RECEIPT = "erpnext.stock.doctype.purchase_receipt.mapper.make_purchase_invoice"
SALES_ORDER_FROM_QUOTATION = "erpnext.selling.doctype.quotation.mapper.make_sales_order"
DELIVERY_NOTE_FROM_ORDER = "erpnext.selling.doctype.sales_order.mapper.make_delivery_note"
SALES_INVOICE_FROM_ORDER = "erpnext.selling.doctype.sales_order.mapper.make_sales_invoice"
SALES_INVOICE_FROM_DELIVERY_NOTE = "erpnext.stock.doctype.delivery_note.mapper.make_sales_invoice"


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
							self.assertEqual(receipt.apply_discount_on, "Net Total")
							self.assertEqual(receipt.discount_amount, percentage)
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

	def test_fixed_discount_remainder_after_multiple_partial_receipts(self):
		for apply_discount_on in ("Net Total", "Grand Total"):
			for inclusive in (False, True):
				for discounted_first in (False, True):
					with self.subTest(
						basis=apply_discount_on, inclusive=inclusive, discounted_first=discounted_first
					):
						rate = 110 if inclusive else 100
						discounted = self.make_order(
							qty=10,
							rate=rate,
							fixed=100,
							inclusive=inclusive,
							apply_discount_on=apply_discount_on,
						)
						first = make_purchase_receipt(discounted.name)
						first.items[0].qty = 2
						first.discount_amount = 20
						first.save().submit()
						regular = self.make_order(item="_Test Item 2", qty=5, rate=rate, inclusive=inclusive)
						sources = (discounted, regular) if discounted_first else (regular, discounted)
						second = self.combine(*sources)
						item = second.getone("items", {"purchase_order": discounted.name})
						self.assertEqual(item.qty, 8)
						expected_per_unit = (
							100 / 11 if inclusive and apply_discount_on == "Grand Total" else 10
						)
						self.assertAlmostEqual(
							item.mapped_additional_discount_amount, expected_per_unit, places=3
						)
						item.qty = 3
						second.save().submit()
						third = make_purchase_receipt(discounted.name).save().submit()
						self.assertEqual(third.items[0].qty, 5)
						self.assertEqual(third.discount_amount, 50)
						self.assertEqual(
							first.grand_total + second.grand_total + third.grand_total,
							discounted.grand_total + regular.grand_total,
						)

	def test_three_fixed_sources_keep_their_own_discounts(self):
		third_item = make_item("_Test Third Mapped Discount Item").name
		orders = [
			self.make_order(item=item, qty=10, fixed=discount)
			for item, discount in (("_Test Item", 100), ("_Test Item 2", 200), (third_item, 300))
		]
		for sources in (orders, list(reversed(orders))):
			receipt = self.combine(*sources).save()
			self.assertEqual([item.idx for item in receipt.items], [1, 2, 3])
			receipt.reload()
			self.assertEqual(
				[item.purchase_order for item in receipt.items], [source.name for source in sources]
			)
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
			invoice = self.combine(
				regular, discounted, mapper=SALES_INVOICE_FROM_ORDER, doctype="Sales Invoice"
			)
			self.assertEqual([item.idx for item in invoice.items], [1, 2])
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

	def test_partially_used_fixed_discounts_of_several_orders(self):
		orders = []
		for item, discount, used in (("_Test Item", 100, 50), ("_Test Item 2", 200, 100)):
			order = self.make_order(item=item, qty=10, fixed=discount)
			receipt = make_purchase_receipt(order.name)
			receipt.items[0].qty = 5
			receipt.discount_amount = used
			receipt.save().submit()
			orders.append(order)

		for sources in (orders, list(reversed(orders))):
			self.assertEqual(self.combine(*sources).save().grand_total, 850)

	def test_percentage_discounts_of_purchase_documents(self):
		regular_item = make_item("_Test Mixed Purchase Discount Item").name
		for apply_discount_on in ("Net Total", "Grand Total"):
			orders = [
				self.make_order(item=item, percentage=percentage, apply_discount_on=apply_discount_on)
				for item, percentage in (("_Test Item", 10), ("_Test Item 2", 20), (regular_item, 0))
			]
			expected_net_amounts = dict(zip([order.name for order in orders], (90, 80, 100), strict=True))
			for sources in (orders, list(reversed(orders))):
				with self.subTest(basis=apply_discount_on, mapper=PURCHASE_RECEIPT_FROM_ORDER):
					receipt = self.combine(*sources).save()
					self.assert_percentage_discounts(receipt, "purchase_order", expected_net_amounts)

			receipts = [make_purchase_receipt(order.name).save().submit() for order in orders]
			for mapper, sources in (
				(PURCHASE_INVOICE_FROM_ORDER, orders),
				(PURCHASE_INVOICE_FROM_RECEIPT, receipts),
			):
				for ordered_sources in (sources, list(reversed(sources))):
					with self.subTest(basis=apply_discount_on, mapper=mapper):
						invoice = self.combine(*ordered_sources, mapper=mapper, doctype="Purchase Invoice")
						invoice.save()
						self.assert_percentage_discounts(invoice, "purchase_order", expected_net_amounts)

	def test_percentage_discounts_of_sales_documents(self):
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

		self.enterContext(self.change_settings("Stock Settings", allow_negative_stock=1))
		self.enterContext(
			self.change_settings(
				"Selling Settings", maintain_same_sales_rate=1, maintain_same_rate_action="Stop"
			)
		)
		regular_item = make_item("_Test Mixed Sales Discount Item").name
		for apply_discount_on in ("Net Total", "Grand Total"):
			orders = [
				self.make_sales_order(item=item, percentage=percentage, apply_discount_on=apply_discount_on)
				for item, percentage in (("_Test Item", 10), ("_Test Item 2", 20), (regular_item, 0))
			]

			expected_net_amounts = dict(zip([order.name for order in orders], (90, 80, 100), strict=True))
			for sources in (orders, list(reversed(orders))):
				with self.subTest(basis=apply_discount_on, mapper=DELIVERY_NOTE_FROM_ORDER):
					delivery_note = self.combine(
						*sources, mapper=DELIVERY_NOTE_FROM_ORDER, doctype="Delivery Note"
					).save()
					self.assert_percentage_discounts(
						delivery_note, "against_sales_order", expected_net_amounts
					)
					delivery_note.items[0].rate -= 1
					with self.assertRaisesRegex(frappe.ValidationError, "Rate must be same"):
						delivery_note.save()

			delivery_notes = [make_delivery_note(order.name).save().submit() for order in orders]
			for mapper, sources in (
				(SALES_INVOICE_FROM_ORDER, orders),
				(SALES_INVOICE_FROM_DELIVERY_NOTE, delivery_notes),
			):
				for ordered_sources in (sources, list(reversed(sources))):
					with self.subTest(basis=apply_discount_on, mapper=mapper):
						invoice = self.combine(*ordered_sources, mapper=mapper, doctype="Sales Invoice")
						invoice.save()
						self.assert_percentage_discounts(invoice, "sales_order", expected_net_amounts)

	def test_matching_percentage_discounts_stay_on_the_header(self):
		for apply_discount_on in ("Net Total", "Grand Total"):
			orders = [
				self.make_order(item=item, percentage=10, apply_discount_on=apply_discount_on)
				for item in ("_Test Item", "_Test Item 2")
			]
			invoice = self.combine(*orders, mapper=PURCHASE_INVOICE_FROM_ORDER, doctype="Purchase Invoice")
			invoice.save()
			self.assertEqual(invoice.apply_discount_on, apply_discount_on)
			self.assertEqual(invoice.additional_discount_percentage, 10)
			self.assertEqual(invoice.discount_amount, 20)
			self.assertEqual(invoice.grand_total, 180)
			for item in invoice.items:
				self.assertEqual(item.rate, 100)
				self.assertEqual(item.net_rate, 90)
				self.assertEqual(item.mapped_additional_discount_amount, 0)

	def test_purchase_order_from_sales_order_skips_the_sales_discount(self):
		from erpnext.selling.doctype.sales_order.mapper import make_purchase_order

		sales_order = self.make_combined_sales_order()
		self.assertEqual(sales_order.items[0].mapped_additional_discount_amount, 10)

		purchase_order = make_purchase_order(
			sales_order.name, [{"item_code": "_Test Item", "supplier": "_Test Supplier"}]
		)[0]
		self.assertEqual(purchase_order.items[0].mapped_additional_discount_amount, 0)
		self.assertEqual(purchase_order.net_total, purchase_order.total)

	def test_fixed_discount_remainder_ignores_other_carried_discounts(self):
		fixed = self.make_order(qty=10, fixed=100)
		percentage = self.make_order(item="_Test Item 2", percentage=20)
		combined = self.combine(fixed, percentage)
		combined.getone("items", {"purchase_order": fixed.name}).qty = 5
		combined.save().submit()
		self.assertEqual(combined.discount_amount, 70)

		remaining = make_purchase_receipt(fixed.name).save()
		self.assertEqual(remaining.discount_amount, 50)

	def test_discount_accounting_books_carried_discounts(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		self.enterContext(self.change_settings("Selling Settings", enable_discount_accounting=1))
		discount_account = create_account(
			account_name="Discount Account", parent_account="Indirect Expenses - _TC", company="_Test Company"
		)
		orders = [
			self.make_sales_order(item=item, percentage=percentage)
			for item, percentage in (("_Test Item", 10), ("_Test Item 2", 0))
		]
		invoice = self.combine(*orders, mapper=SALES_INVOICE_FROM_ORDER, doctype="Sales Invoice")
		invoice.additional_discount_account = discount_account
		invoice.save().submit()

		ledger = {}
		for entry in frappe.get_all("GL Entry", {"voucher_no": invoice.name}, ["account", "debit", "credit"]):
			debit, credit = ledger.get(entry.account, (0, 0))
			ledger[entry.account] = (debit + entry.debit, credit + entry.credit)

		self.assertEqual(ledger[discount_account], (10, 0))
		self.assertEqual(ledger["Sales - _TC"], (0, 200))
		self.assertEqual(ledger["Debtors - _TC"], (190, 0))

	def test_cash_discount_is_kept_when_an_undiscounted_order_is_added(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		first = self.make_sales_order()
		second = self.make_sales_order(item="_Test Item 2")
		invoice = self.make_invoice_with_cash_discount(first)

		invoice = make_sales_invoice(second.name, invoice.as_dict())
		self.assertEqual(invoice.is_cash_or_non_trade_discount, 1)
		self.assertEqual(invoice.apply_discount_on, "Grand Total")
		self.assertEqual(invoice.discount_amount, 5)
		self.assertEqual(invoice.grand_total, 195)

	def test_cash_discount_cannot_be_combined_with_carried_discounts(self):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		regular = self.make_sales_order()
		discounted = self.make_sales_order(item="_Test Item 2", percentage=10)
		invoice = self.make_invoice_with_cash_discount(regular)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be combined"):
			make_sales_invoice(discounted.name, invoice.as_dict())

		combined = self.combine(regular, discounted, mapper=SALES_INVOICE_FROM_ORDER, doctype="Sales Invoice")
		combined.is_cash_or_non_trade_discount = 1
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be combined"):
			combined.save()

	def test_changing_the_item_drops_its_carried_discount(self):
		discounted = self.make_sales_order(percentage=10)
		regular = self.make_sales_order(item="_Test Item 2")
		invoice = self.combine(discounted, regular, mapper=SALES_INVOICE_FROM_ORDER, doctype="Sales Invoice")
		invoice.save()
		row = invoice.getone("items", {"sales_order": discounted.name})
		self.assertEqual(row.mapped_additional_discount_amount, 10)

		row.item_code = make_item("_Test Mixed Replacement Item").name
		invoice.process_item_selection(row.idx, reset_item_details=True)
		invoice.calculate_taxes_and_totals()
		self.assertFalse(row.mapped_additional_discount_amount)
		self.assertEqual(invoice.discount_amount, 0)

	def test_billed_rejected_quantity_uses_its_carried_discount(self):
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

		self.enterContext(
			self.change_settings(
				"Buying Settings",
				bill_for_rejected_quantity_in_purchase_invoice=1,
				set_valuation_rate_for_rejected_materials=1,
			)
		)
		fixed = self.make_order(qty=10, fixed=100)
		regular = self.make_order(item="_Test Item 2")
		invoice = self.combine(fixed, regular, mapper=PURCHASE_INVOICE_FROM_ORDER, doctype="Purchase Invoice")
		invoice.update_stock = 1
		row = invoice.getone("items", {"purchase_order": fixed.name})
		row.update(
			{
				"received_qty": 5,
				"qty": 3,
				"rejected_qty": 2,
				"rejected_warehouse": "_Test Rejected Warehouse - _TC",
			}
		)
		invoice.save().submit()
		self.assertEqual(row.distributed_discount_amount, 50)

		remaining = make_purchase_invoice(fixed.name).save()
		self.assertEqual(remaining.discount_amount, 50)

	def test_removing_the_last_discounted_row_clears_the_header(self):
		discounted = self.make_sales_order(percentage=10)
		regular = self.make_sales_order(item="_Test Item 2")
		invoice = self.combine(discounted, regular, mapper=SALES_INVOICE_FROM_ORDER, doctype="Sales Invoice")
		invoice.save()

		invoice.remove(invoice.getone("items", {"sales_order": discounted.name}))
		invoice.save()
		self.assertEqual(invoice.discount_amount, 0)
		self.assertEqual(invoice.grand_total, 100)

	def test_update_items_removing_the_last_discounted_row_clears_the_header(self):
		from erpnext.accounts.services.child_item_update import update_child_qty_rate

		sales_order = self.make_combined_sales_order()
		regular = sales_order.items[1]
		update_child_qty_rate(
			"Sales Order",
			frappe.as_json(
				[
					{
						"docname": regular.name,
						"item_code": regular.item_code,
						"qty": regular.qty,
						"rate": regular.rate,
					}
				]
			),
			sales_order.name,
		)

		sales_order.reload()
		self.assertEqual(sales_order.discount_amount, 0)
		self.assertEqual(sales_order.grand_total, 100)

	def test_update_items_replacing_the_last_discounted_row_clears_the_header(self):
		from erpnext.accounts.services.child_item_update import update_child_qty_rate

		sales_order = self.make_combined_sales_order()
		regular = sales_order.items[1]
		update_child_qty_rate(
			"Sales Order",
			frappe.as_json(
				[
					{
						"docname": regular.name,
						"item_code": regular.item_code,
						"qty": regular.qty,
						"rate": 100,
					},
					{
						"item_code": "_Test Item",
						"qty": 1,
						"rate": 100,
						"delivery_date": sales_order.delivery_date,
					},
				]
			),
			sales_order.name,
		)

		sales_order.reload()
		self.assertEqual(sales_order.discount_amount, 0)
		self.assertEqual(sales_order.grand_total, 200)

	def assert_percentage_discounts(self, document, source_field, expected_net_amounts):
		items = {item.get(source_field): item for item in document.items}
		self.assertEqual(document.apply_discount_on, "Net Total")
		self.assertEqual(document.additional_discount_percentage, 0)
		self.assertEqual(document.discount_amount, 30)
		self.assertEqual(document.grand_total, 270)
		for source, net_amount in expected_net_amounts.items():
			self.assertEqual(items[source].rate, 100)
			self.assertEqual(items[source].mapped_additional_discount_amount, 100 - net_amount)
			self.assertEqual(items[source].net_amount, net_amount)

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

	def make_combined_sales_order(self):
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation

		quotations = []
		for item, percentage in (("_Test Item", 10), ("_Test Item 2", 0)):
			quotation = make_quotation(item_code=item, qty=1, rate=100, do_not_save=True)
			quotation.apply_discount_on = "Net Total"
			quotation.additional_discount_percentage = percentage
			quotations.append(quotation.insert().submit())

		sales_order = self.combine(*quotations, mapper=SALES_ORDER_FROM_QUOTATION, doctype="Sales Order")
		sales_order.delivery_date = add_days(nowdate(), 5)
		for item in sales_order.items:
			item.delivery_date = sales_order.delivery_date
		return sales_order.insert().submit()

	def make_invoice_with_cash_discount(self, order):
		from erpnext.selling.doctype.sales_order.mapper import make_sales_invoice

		invoice = make_sales_invoice(order.name)
		invoice.apply_discount_on = "Grand Total"
		invoice.is_cash_or_non_trade_discount = 1
		invoice.discount_amount = 5
		return invoice

	def make_sales_order(self, *, item="_Test Item", percentage=0, apply_discount_on="Net Total"):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		order = make_sales_order(item_code=item, qty=1, rate=100, do_not_save=True)
		order.apply_discount_on = apply_discount_on
		order.additional_discount_percentage = percentage
		return order.save().submit()

	def combine(self, *sources, mapper=PURCHASE_RECEIPT_FROM_ORDER, doctype="Purchase Receipt"):
		return map_docs(mapper, [source.name for source in sources], frappe.new_doc(doctype).as_dict())
