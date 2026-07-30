import frappe

from erpnext.stock.get_item_details import get_item_details
from erpnext.tests.utils import ERPNextTestSuite


class TestGetItemDetail(ERPNextTestSuite):
	def test_get_item_detail_purchase_order(self):
		args = frappe._dict(
			{
				"item_code": "_Test Item",
				"company": "_Test Company 1",
				"customer": "_Test Customer",
				"currency": "USD",
				"conversion_rate": 1.0,
				"price_list_currency": "USD",
				"plc_conversion_rate": 1.0,
				"doctype": "Purchase Order",
				"name": None,
				"supplier": "_Test Supplier",
				"transaction_date": None,
				"price_list": "_Test Buying Price List",
				"is_subcontracted": 0,
				"ignore_pricing_rule": 1,
				"qty": 1,
			}
		)
		details = get_item_details(args)
		self.assertEqual(details.get("price_list_rate"), 100)

	def test_bin_details_for_selling_doctypes(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = make_item(properties={"is_stock_item": 1}).name

		make_purchase_receipt(item_code=item_code, warehouse="_Test Warehouse - _TC", qty=100, rate=100)
		make_purchase_receipt(item_code=item_code, warehouse="_Test Warehouse 1 - _TC", qty=50, rate=100)

		args = frappe._dict(
			{
				"item_code": item_code,
				"warehouse": "_Test Warehouse - _TC",
				"company": "_Test Company",
				"customer": "_Test Customer",
				"currency": "INR",
				"conversion_rate": 1.0,
				"price_list": "_Test Price List",
				"price_list_currency": "INR",
				"plc_conversion_rate": 1.0,
				"transaction_date": None,
				"name": None,
				"ignore_pricing_rule": 1,
				"qty": 1,
			}
		)

		for doctype in ("Sales Order", "Quotation", "Sales Invoice", "Delivery Note", "Purchase Order"):
			with self.subTest(doctype=doctype):
				details = get_item_details(args.copy().update({"doctype": doctype}))

				self.assertEqual(details.get("actual_qty"), 100)
				self.assertEqual(details.get("company_total_stock"), 150)

	# making this test in get_item_details test file as feat/fix is present in that method
	def test_fetch_price_from_list_rate_on_doc_save(self):
		# create item
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Test Item with Batch",
				"item_name": "Test Item with Batch",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
				"has_batch_no": 1,
			}
		).insert()

		# create batch
		frappe.get_doc(
			{
				"doctype": "Batch",
				"batch_id": "BATCH01",
				"item": item.name,
			}
		).insert()

		# create item price
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "Standard Selling",
				"item_code": item.item_code,
				"price_list_rate": 50,
				"batch_no": "BATCH01",
			}
		).insert()

		# create purchase receipt to have some stock for delivery
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		make_purchase_receipt(
			item_code=item.item_code,
			warehouse="_Test Warehouse - _TC",
			qty=100,
			rate=100,
			batch_no="BATCH01",
		)

		# creating sales order just to create delivery note from it
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(item_code=item.item_code, qty=2, rate=75)

		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

		dn = make_delivery_note(so.name)

		# Test 1 : On creation of DN, item's batch won't be fetched and rate will remaing the same as in SO
		self.assertIsNone(dn.items[0].batch_no)
		self.assertEqual(dn.items[0].rate, 75)

		# Test 2 : On saving the DN, item's batch will be fetched and rate will be updated from Item Price
		dn.save()
		self.assertEqual(dn.items[0].batch_no, "BATCH01")
		self.assertEqual(dn.items[0].rate, 50)

	def test_maintain_same_rate_keeps_source_rate_on_refetch(self):
		"""#57436: with "maintain same rate" on, re-fetching a PR row mapped from a
		PO must keep the PO rate instead of pulling a newer, higher Item Price.

		The rate is validated on save, so it can never persist changed; assert the
		fetched rate directly to prove the newer Item Price is never picked up.
		"""
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.item.test_item import make_item

		def set_maintain_same_rate(value):
			frappe.db.set_single_value("Buying Settings", "maintain_same_rate", value)
			frappe.clear_cache(doctype="Buying Settings")

		set_maintain_same_rate(1)

		item_code = make_item(properties={"is_stock_item": 1}).name
		po = create_purchase_order(item_code=item_code, qty=1, rate=100)

		# The PO may auto-insert an Item Price at 100; bump it to the newer, higher rate.
		item_price = frappe.db.get_value(
			"Item Price", {"item_code": item_code, "price_list": "Standard Buying"}
		)
		if item_price:
			frappe.db.set_value("Item Price", item_price, "price_list_rate", 120)
		else:
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "Standard Buying",
					"item_code": item_code,
					"price_list_rate": 120,
				}
			).insert()

		pr = make_purchase_receipt(po.name)
		pr.insert()

		def fetch_price_list_rate():
			ctx = frappe._dict(
				{
					"item_code": item_code,
					"doctype": "Purchase Receipt",
					"name": pr.name,
					"company": pr.company,
					"supplier": pr.supplier,
					"currency": pr.currency,
					"conversion_rate": 1.0,
					"price_list": "Standard Buying",
					"price_list_currency": pr.currency,
					"plc_conversion_rate": 1.0,
					"warehouse": pr.items[0].warehouse,
					"uom": pr.items[0].uom,
					"stock_uom": pr.items[0].stock_uom,
					"qty": pr.items[0].qty,
					"child_doctype": pr.items[0].doctype,
					"child_docname": pr.items[0].name,
					"is_return": 0,
					"is_internal_supplier": 0,
					"ignore_pricing_rule": 1,
				}
			)
			return get_item_details(ctx, pr).get("price_list_rate")

		# Rate stays at the PO rate; the newer Item Price (120) is not fetched.
		self.assertEqual(fetch_price_list_rate(), 100)

		# Control: without the setting the newer Item Price would be fetched.
		set_maintain_same_rate(0)
		self.assertEqual(fetch_price_list_rate(), 120)

	def test_apply_price_list_keeps_source_rate_when_maintain_same_rate(self):
		"""#57436: the bulk apply_price_list path (price list / party / conversion rate
		change) must also keep the source rate on mapped rows, not just re-fetch of a
		single row. Here a PR row carries its PO rate (175) while the current price list
		rate is 100; the bulk apply must keep 175.
		"""
		from frappe.utils import flt, nowdate

		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.get_item_details import apply_price_list

		item_code = "_Test Item"
		price_list = "_Test Buying Price List"

		original = frappe.db.get_single_value("Buying Settings", "maintain_same_rate")
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 1)
		frappe.clear_cache(doctype="Buying Settings")

		try:
			po = create_purchase_order(item_code=item_code, rate=175, qty=1)

			row_name = "pr-row-1"
			pr_doc = {
				"doctype": "Purchase Receipt",
				"items": [
					{
						"name": row_name,
						"item_code": item_code,
						"purchase_order_item": po.items[0].name,
						"price_list_rate": 175,
						"rate": 175,
					}
				],
			}
			ctx = frappe._dict(
				doctype="Purchase Receipt",
				supplier=po.supplier,
				company=po.company,
				currency=po.currency,
				conversion_rate=1.0,
				price_list=price_list,
				plc_conversion_rate=1.0,
				transaction_date=nowdate(),
				items=[
					frappe._dict(
						doctype="Purchase Receipt Item",
						parenttype="Purchase Receipt",
						item_code=item_code,
						child_docname=row_name,
						qty=1,
						uom=po.items[0].uom,
						stock_uom=po.items[0].stock_uom,
						conversion_factor=1.0,
					)
				],
			)

			result = apply_price_list(ctx, doc=pr_doc)
			self.assertEqual(flt(result["children"][0].get("price_list_rate")), 175)
		finally:
			frappe.db.set_single_value("Buying Settings", "maintain_same_rate", original)
			frappe.clear_cache(doctype="Buying Settings")
