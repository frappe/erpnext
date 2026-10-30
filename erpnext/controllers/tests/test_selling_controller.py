# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestSellingControllerConversions(ERPNextTestSuite):
	def test_gross_profit_uses_company_currency(self):
		self.load_test_records("Sales Order")
		self.load_test_records("Quotation")
		item = make_item(
			properties={"is_stock_item": 1, "stock_uom": "Nos"},
			uoms=[{"uom": "Box", "conversion_factor": 5}],
		)
		make_stock_entry(item_code=item.name, target="_Test Warehouse - _TC", qty=50, basic_rate=5200)

		for make_document in (make_sales_order, make_quotation):
			for currency, conversion_rate, rate in (("INR", 1, 8300), ("USD", 83, 100)):
				for uom, conversion_factor in (("Nos", 1), ("Box", 5)):
					with self.subTest(doctype=make_document.__name__, currency=currency, uom=uom):
						doc = make_document(
							item_code=item.name,
							qty=2,
							rate=rate * conversion_factor,
							uom=uom,
							currency=currency,
							do_not_save=True,
						)
						doc.conversion_rate = conversion_rate
						doc.insert().submit()
						doc.reload()
						self.assertEqual(doc.docstatus, 1)
						self.assertEqual(doc.items[0].base_net_rate, 8300 * conversion_factor)
						self.assertEqual(doc.items[0].valuation_rate, 5200)
						self.assertEqual(doc.items[0].stock_qty, 2 * conversion_factor)
						self.assertEqual(doc.items[0].gross_profit, 6200 * conversion_factor)

	def test_partial_delivery_updates_sales_order_status(self):
		# Submitting a Delivery Note against a Sales Order calls
		# SellingController.get_already_delivered_qty / get_so_qty_and_warehouse and StatusUpdater
		# (per_delivered via coalesce(sum(...))) -- all converted to query builder / ORM here.
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)

		so = make_sales_order(qty=10)

		dn = make_delivery_note(so.name)
		dn.items[0].qty = 4
		dn.insert()
		dn.submit()

		so.reload()
		self.assertEqual(so.per_delivered, 40.0)
