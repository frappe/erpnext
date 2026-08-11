import frappe
from frappe import qb
from frappe.utils import today

from erpnext.tests.utils import ERPNextTestSuite


class TestReactivity(ERPNextTestSuite):
	def test_01_basic_item_details(self):
		# set Item Price
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": "_Test Item",
				"price_list": "Standard Selling",
				"price_list_rate": 90,
				"selling": True,
				"rate": 90,
				"valid_from": today(),
			}
		).insert()

		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"debit_to": "Debtors - _TC",
				"posting_date": today(),
				"cost_center": "Main - _TC",
				"currency": "INR",
				"conversion_rate": 1,
				"selling_price_list": "Standard Selling",
			}
		)
		itm = si.append("items")
		itm.item_code = "_Test Item"
		si.process_item_selection(itm.idx)
		self.assertEqual(itm.rate, 90)

		df = qb.DocType("DocField")
		_res = (
			qb.from_(df).select(df.fieldname).where(df.parent.eq("Sales Invoice Item") & df.reqd.eq(1)).run()
		)
		for field in _res:
			with self.subTest(field=field):
				self.assertIsNotNone(itm.get(field[0]))
		si.save().submit()

	def test_item_change_clears_stale_item_details(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		old_item = make_item(properties={"is_stock_item": 0, "stock_uom": "Nos"})
		new_item = make_item(
			properties={
				"is_stock_item": 0,
				"stock_uom": "Kg",
				"weight_per_unit": 2,
				"weight_uom": "Kg",
			}
		)
		sales_order = make_sales_order(item_code=old_item.name, do_not_submit=True)

		item = sales_order.items[0]
		self.assertEqual(item.uom, "Nos")
		row_state = (item.qty, item.warehouse, item.delivery_date)

		sales_order.ignore_pricing_rule = 1
		item.weight_per_unit = 10
		item.weight_uom = "Nos"
		item.barcode = "OLD-BARCODE"
		item.pricing_rules = "OLD-PRICING-RULE"
		item.item_code = new_item.name
		sales_order.process_item_selection(item.idx, reset_item_details=True)

		self.assertEqual(item.uom, "Kg")
		self.assertEqual(item.stock_uom, "Kg")
		self.assertEqual(item.conversion_factor, 1)
		self.assertEqual(item.weight_per_unit, 2)
		self.assertEqual(item.weight_uom, "Kg")
		self.assertIsNone(item.barcode)
		self.assertFalse(item.pricing_rules)
		self.assertEqual((item.qty, item.warehouse, item.delivery_date), row_state)

	def test_programmatic_item_selection_preserves_explicit_uom(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={
				"is_stock_item": 0,
				"stock_uom": "Kg",
				"sales_uom": "Nos",
				"weight_per_unit": 2,
				"weight_uom": "Kg",
			},
			uoms=[{"uom": "Nos", "conversion_factor": 10}],
		)
		sales_invoice = create_sales_invoice(item_code=item.name, uom="Kg", do_not_save=True)

		sales_invoice.process_item_selection(sales_invoice.items[0].idx)

		self.assertEqual(sales_invoice.items[0].uom, "Kg")
		self.assertEqual(sales_invoice.items[0].conversion_factor, 1)
		self.assertEqual(sales_invoice.items[0].stock_qty, sales_invoice.items[0].qty)
