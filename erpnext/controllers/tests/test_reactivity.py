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

	def add_optional_items_table(self):
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

		create_custom_fields(
			{
				"Sales Order": [
					{
						"fieldname": "optional_items",
						"label": "Optional Items",
						"fieldtype": "Table",
						"options": "Sales Order Item",
						"insert_after": "items",
					}
				]
			}
		)
		self.addCleanup(frappe.clear_cache, doctype="Sales Order")
		self.addCleanup(frappe.delete_doc, "Custom Field", "Sales Order-optional_items")

	def make_sales_order_with_optional_items(self, item_code, optional_item_codes):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		self.add_optional_items_table()
		sales_order = make_sales_order(item_code=item_code, uom="Kg", rate=500, do_not_save=True)
		for optional_item_code in optional_item_codes:
			sales_order.append("optional_items", {"item_code": optional_item_code, "qty": 1})

		return sales_order

	def test_item_selection_updates_the_row_in_its_own_child_table(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		optional_item = make_item(properties={"is_stock_item": 0, "stock_uom": "Nos"})
		sales_order = self.make_sales_order_with_optional_items(item.name, [item.name, optional_item.name])

		standard_row = sales_order.items[0]
		row_state = (standard_row.item_code, standard_row.uom, standard_row.rate)
		edited_row = sales_order.optional_items[1]

		sales_order.process_item_selection(
			edited_row.idx, reset_item_details=True, parentfield="optional_items"
		)

		self.assertEqual(edited_row.item_name, optional_item.item_name)
		self.assertEqual(edited_row.uom, "Nos")
		self.assertEqual((standard_row.item_code, standard_row.uom, standard_row.rate), row_state)

	def test_item_selection_ignores_a_row_that_is_gone(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		sales_order = self.make_sales_order_with_optional_items(item.name, [])

		sales_order.process_item_selection(len(sales_order.items) + 1)

		self.assertEqual(len(sales_order.items), 1)

	def test_item_selection_rejects_a_field_that_is_not_a_child_table(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		sales_order = self.make_sales_order_with_optional_items(item.name, [])

		self.assertRaises(
			frappe.ValidationError, sales_order.process_item_selection, 1, parentfield="company"
		)

	def test_free_item_is_added_to_the_table_that_earned_it(self):
		from erpnext.accounts.doctype.pricing_rule.test_pricing_rule import make_pricing_rule
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		optional_item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		free_item = make_item(properties={"is_stock_item": 0, "stock_uom": "Kg"})
		make_pricing_rule(
			title=f"_Test Free Item Rule {optional_item.name}",
			selling=1,
			item_code=optional_item.name,
			price_or_product_discount="Product",
			free_item=free_item.name,
			free_qty=1,
		)
		sales_order = self.make_sales_order_with_optional_items(item.name, [optional_item.name])

		sales_order.process_item_selection(sales_order.optional_items[0].idx, parentfield="optional_items")

		self.assertEqual([row.item_code for row in sales_order.items], [item.name])
		self.assertEqual(
			[row.item_code for row in sales_order.optional_items],
			[optional_item.name, free_item.name],
		)
