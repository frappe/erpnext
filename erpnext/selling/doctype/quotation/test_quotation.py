# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, getdate, nowdate

test_dependencies = ["Product Bundle"]


class TestQuotation(FrappeTestCase):
	def test_make_quotation_without_terms(self):
		quotation = make_quotation(do_not_save=1)
		self.assertFalse(quotation.get("payment_schedule"))

		quotation.insert()

		self.assertTrue(quotation.payment_schedule)

	def test_make_sales_order_terms_copied(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)

		self.assertTrue(sales_order.get("payment_schedule"))

	def test_gross_profit(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
		from erpnext.stock.get_item_details import insert_item_price

		item_doc = make_item("_Test Item for Gross Profit", {"is_stock_item": 1})
		item_code = item_doc.name
		make_stock_entry(item_code=item_code, qty=10, rate=100, target="_Test Warehouse - _TC")

		selling_price_list = frappe.get_all("Price List", filters={"selling": 1}, limit=1)[0].name
		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 1)
		insert_item_price(
			frappe._dict(
				{
					"item_code": item_code,
					"price_list": selling_price_list,
					"price_list_rate": 300,
					"rate": 300,
					"conversion_factor": 1,
					"discount_amount": 0.0,
					"currency": frappe.db.get_value("Price List", selling_price_list, "currency"),
					"uom": item_doc.stock_uom,
				}
			)
		)

		quotation = make_quotation(
			item_code=item_code, qty=1, rate=300, selling_price_list=selling_price_list
		)
		self.assertEqual(quotation.items[0].valuation_rate, 100)
		self.assertEqual(quotation.items[0].gross_profit, 200)
		frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)

	def test_maintain_rate_in_sales_cycle_is_enforced(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		maintain_rate = frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate")
		frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", 1)

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.items[0].rate = 1
		self.assertRaises(frappe.ValidationError, sales_order.save)

		frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", maintain_rate)

	def test_make_sales_order_with_different_currency(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.currency = "USD"
		sales_order.conversion_rate = 20.0
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.delivery_date = nowdate()
		sales_order.insert()

		self.assertEqual(sales_order.currency, "USD")
		self.assertNotEqual(sales_order.currency, quotation.currency)

	def test_make_sales_order(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)

		self.assertEqual(sales_order.doctype, "Sales Order")
		self.assertEqual(len(sales_order.get("items")), 1)
		self.assertEqual(sales_order.get("items")[0].doctype, "Sales Order Item")
		self.assertEqual(sales_order.get("items")[0].prevdoc_docname, quotation.name)
		self.assertEqual(sales_order.customer, "_Test Customer")

		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.delivery_date = nowdate()
		sales_order.insert()

	def test_make_sales_order_with_terms(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.update({"payment_terms_template": "_Test Payment Term Template"})
		quotation.insert()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.save()
		quotation.submit()

		self.assertEqual(quotation.payment_schedule[0].payment_amount, 8906.00)
		self.assertEqual(quotation.payment_schedule[0].due_date, quotation.transaction_date)
		self.assertEqual(quotation.payment_schedule[1].payment_amount, 8906.00)
		self.assertEqual(quotation.payment_schedule[1].due_date, add_days(quotation.transaction_date, 30))

		sales_order = make_sales_order(quotation.name)

		self.assertEqual(sales_order.doctype, "Sales Order")
		self.assertEqual(len(sales_order.get("items")), 1)
		self.assertEqual(sales_order.get("items")[0].doctype, "Sales Order Item")
		self.assertEqual(sales_order.get("items")[0].prevdoc_docname, quotation.name)
		self.assertEqual(sales_order.customer, "_Test Customer")

		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.delivery_date = nowdate()
		sales_order.insert()

		# Remove any unknown taxes if applied
		sales_order.set("taxes", [])
		sales_order.save()

		self.assertEqual(sales_order.payment_schedule[0].payment_amount, 8906.00)
		self.assertEqual(sales_order.payment_schedule[0].due_date, getdate(quotation.transaction_date))
		self.assertEqual(sales_order.payment_schedule[1].payment_amount, 8906.00)
		self.assertEqual(
			sales_order.payment_schedule[1].due_date, getdate(add_days(quotation.transaction_date, 30))
		)

	def test_valid_till_before_transaction_date(self):
		quotation = frappe.copy_doc(test_records[0])
		quotation.valid_till = add_days(quotation.transaction_date, -1)
		self.assertRaises(frappe.ValidationError, quotation.validate)

	def test_so_from_expired_quotation(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		frappe.db.set_single_value("Selling Settings", "allow_sales_order_creation_for_expired_quotation", 0)

		quotation = frappe.copy_doc(test_records[0])
		quotation.valid_till = add_days(nowdate(), -1)
		quotation.insert()
		quotation.submit()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)

		frappe.db.set_single_value("Selling Settings", "allow_sales_order_creation_for_expired_quotation", 1)

		make_sales_order(quotation.name)

	def test_create_quotation_with_margin(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_delivery_note,
			make_sales_invoice,
		)

		rate_with_margin = flt((1500 * 18.75) / 100 + 1500)

		test_records[0]["items"][0]["price_list_rate"] = 1500
		test_records[0]["items"][0]["margin_type"] = "Percentage"
		test_records[0]["items"][0]["margin_rate_or_amount"] = 18.75

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()

		self.assertEqual(quotation.get("items")[0].rate, rate_with_margin)
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = "2016-01-01"
		sales_order.delivery_date = "2016-01-02"

		sales_order.insert()

		self.assertEqual(quotation.get("items")[0].rate, rate_with_margin)

		sales_order.submit()

		dn = make_delivery_note(sales_order.name)
		self.assertEqual(quotation.get("items")[0].rate, rate_with_margin)
		dn.save()

		si = make_sales_invoice(sales_order.name)
		self.assertEqual(quotation.get("items")[0].rate, rate_with_margin)
		si.save()

	def test_create_two_quotations(self):
		from erpnext.stock.doctype.item.test_item import make_item

		first_item = make_item("_Test Laptop", {"is_stock_item": 1})

		second_item = make_item("_Test CPU", {"is_stock_item": 1})

		qo_item1 = [
			{
				"item_code": first_item.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		qo_item2 = [
			{
				"item_code": second_item.item_code,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 2,
				"rate": 300,
				"conversion_factor": 1.0,
			}
		]

		first_qo = make_quotation(item_list=qo_item1, do_not_submit=True)
		first_qo.submit()
		sec_qo = make_quotation(item_list=qo_item2, do_not_submit=True)
		sec_qo.submit()

	def test_quotation_expiry(self):
		from erpnext.selling.doctype.quotation.quotation import set_expired_status

		quotation_item = [{"item_code": "_Test Item", "warehouse": "", "qty": 1, "rate": 500}]

		yesterday = add_days(nowdate(), -1)
		expired_quotation = make_quotation(
			item_list=quotation_item, transaction_date=yesterday, do_not_submit=True
		)
		expired_quotation.valid_till = yesterday
		expired_quotation.save()
		expired_quotation.submit()
		set_expired_status()
		expired_quotation.reload()
		self.assertEqual(expired_quotation.status, "Expired")

	def test_product_bundle_mapping_on_creating_so(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		quotation = make_quotation(item_code="_Test Product Bundle", qty=1, rate=100)
		sales_order = make_sales_order(quotation.name)

		quotation_item = [
			quotation.items[0].item_code,
			quotation.items[0].rate,
			quotation.items[0].qty,
			quotation.items[0].amount,
		]
		so_item = [
			sales_order.items[0].item_code,
			sales_order.items[0].rate,
			sales_order.items[0].qty,
			sales_order.items[0].amount,
		]

		self.assertEqual(quotation_item, so_item)

		quotation_packed_items = [
			[
				quotation.packed_items[0].parent_item,
				quotation.packed_items[0].item_code,
				quotation.packed_items[0].qty,
			],
			[
				quotation.packed_items[1].parent_item,
				quotation.packed_items[1].item_code,
				quotation.packed_items[1].qty,
			],
		]
		so_packed_items = [
			[
				sales_order.packed_items[0].parent_item,
				sales_order.packed_items[0].item_code,
				sales_order.packed_items[0].qty,
			],
			[
				sales_order.packed_items[1].parent_item,
				sales_order.packed_items[1].item_code,
				sales_order.packed_items[1].qty,
			],
		]

		self.assertEqual(quotation_packed_items, so_packed_items)

	def test_product_bundle_price_calculation_when_calculate_bundle_price_is_unchecked(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Product Bundle", {"is_stock_item": 0})
		bundle_item1 = make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		bundle_item2 = make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		bundle_item1.valuation_rate = 100
		bundle_item1.save()

		bundle_item2.valuation_rate = 200
		bundle_item2.save()

		quotation = make_quotation(item_code="_Test Product Bundle", qty=2, rate=100)
		self.assertEqual(quotation.items[0].amount, 200)

	def test_product_bundle_price_calculation_when_calculate_bundle_price_is_checked(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Product Bundle", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle", ["_Test Bundle Item 1", "_Test Bundle Item 2"])

		enable_calculate_bundle_price()

		quotation = make_quotation(item_code="_Test Product Bundle", qty=2, rate=100, do_not_submit=1)
		quotation.packed_items[0].rate = 100
		quotation.packed_items[1].rate = 200
		quotation.save()

		self.assertEqual(quotation.items[0].amount, 600)
		self.assertEqual(quotation.items[0].rate, 300)

		enable_calculate_bundle_price(enable=0)

	def test_product_bundle_price_calculation_for_multiple_product_bundles_when_calculate_bundle_price_is_checked(
		self,
	):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Product Bundle 1", {"is_stock_item": 0})
		make_item("_Test Product Bundle 2", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})
		make_item("_Test Bundle Item 3", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle 1", ["_Test Bundle Item 1", "_Test Bundle Item 2"])
		make_product_bundle("_Test Product Bundle 2", ["_Test Bundle Item 2", "_Test Bundle Item 3"])

		enable_calculate_bundle_price()

		item_list = [
			{
				"item_code": "_Test Product Bundle 1",
				"warehouse": "",
				"qty": 1,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": "_Test Product Bundle 2",
				"warehouse": "",
				"qty": 1,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
		]

		quotation = make_quotation(item_list=item_list, do_not_submit=1)
		quotation.packed_items[0].rate = 100
		quotation.packed_items[1].rate = 200
		quotation.packed_items[2].rate = 200
		quotation.packed_items[3].rate = 300
		quotation.save()

		expected_values = [300, 500]

		for item in quotation.items:
			self.assertEqual(item.amount, expected_values[item.idx - 1])

		enable_calculate_bundle_price(enable=0)

	def test_packed_items_indices_are_reset_when_product_bundle_is_deleted_from_items_table(self):
		from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Product Bundle 1", {"is_stock_item": 0})
		make_item("_Test Product Bundle 2", {"is_stock_item": 0})
		make_item("_Test Product Bundle 3", {"is_stock_item": 0})
		make_item("_Test Bundle Item 1", {"is_stock_item": 1})
		make_item("_Test Bundle Item 2", {"is_stock_item": 1})
		make_item("_Test Bundle Item 3", {"is_stock_item": 1})

		make_product_bundle("_Test Product Bundle 1", ["_Test Bundle Item 1", "_Test Bundle Item 2"])
		make_product_bundle("_Test Product Bundle 2", ["_Test Bundle Item 2", "_Test Bundle Item 3"])
		make_product_bundle("_Test Product Bundle 3", ["_Test Bundle Item 3", "_Test Bundle Item 1"])

		item_list = [
			{
				"item_code": "_Test Product Bundle 1",
				"warehouse": "",
				"qty": 1,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": "_Test Product Bundle 2",
				"warehouse": "",
				"qty": 1,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
			{
				"item_code": "_Test Product Bundle 3",
				"warehouse": "",
				"qty": 1,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			},
		]

		quotation = make_quotation(item_list=item_list, do_not_submit=1)
		del quotation.items[1]
		quotation.save()

		for id, item in enumerate(quotation.packed_items):
			expected_index = id + 1
			self.assertEqual(item.idx, expected_index)

	def test_alternative_items_with_stock_items(self):
		"""
		Check if taxes & totals considers only non-alternative items with:
		- One set of non-alternative & alternative items [first 3 rows]
		- One simple stock item
		"""
		from erpnext.stock.doctype.item.test_item import make_item

		item_list = []
		stock_items = {
			"_Test Simple Item 1": 100,
			"_Test Alt 1": 120,
			"_Test Alt 2": 110,
			"_Test Simple Item 2": 200,
		}

		for item, rate in stock_items.items():
			make_item(item, {"is_stock_item": 1})
			item_list.append(
				{
					"item_code": item,
					"qty": 1,
					"rate": rate,
					"is_alternative": bool("Alt" in item),
				}
			)

		quotation = make_quotation(item_list=item_list, do_not_submit=1)
		quotation.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 10,
			},
		)
		quotation.submit()

		self.assertEqual(quotation.net_total, 300)
		self.assertEqual(quotation.grand_total, 330)

	def test_alternative_items_with_service_items(self):
		"""
		Check if taxes & totals considers only non-alternative items with:
		- One set of non-alternative & alternative service items [first 3 rows]
		- One simple non-alternative service item
		All having the same item code and unique item name/description due to
		dynamic services
		"""
		from erpnext.stock.doctype.item.test_item import make_item

		item_list = []
		service_items = {
			"Tiling with Standard Tiles": 100,
			"Alt Tiling with Durable Tiles": 150,
			"Alt Tiling with Premium Tiles": 180,
			"False Ceiling with Material #234": 190,
		}

		make_item("_Test Dynamic Service Item", {"is_stock_item": 0})

		for name, rate in service_items.items():
			item_list.append(
				{
					"item_code": "_Test Dynamic Service Item",
					"item_name": name,
					"description": name,
					"qty": 1,
					"rate": rate,
					"is_alternative": bool("Alt" in name),
				}
			)

		quotation = make_quotation(item_list=item_list, do_not_submit=1)
		quotation.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 10,
				"included_in_print_rate": 1,
			},
		)
		quotation.submit()

		self.assertEqual(round(quotation.items[1].net_rate, 2), 136.36)
		self.assertEqual(round(quotation.items[1].amount, 2), 150)

		self.assertEqual(round(quotation.items[2].net_rate, 2), 163.64)
		self.assertEqual(round(quotation.items[2].amount, 2), 180)

		self.assertEqual(round(quotation.net_total, 2), 263.64)
		self.assertEqual(round(quotation.total_taxes_and_charges, 2), 26.36)
		self.assertEqual(quotation.grand_total, 290)

	def test_amount_calculation_for_alternative_items(self):
		"""Make sure that the amount is calculated correctly for alternative items when the qty is changed."""
		from erpnext.stock.doctype.item.test_item import make_item

		item_list = []
		stock_items = {
			"_Test Simple Item 1": 100,
			"_Test Alt 1": 120,
		}

		for item, rate in stock_items.items():
			make_item(item, {"is_stock_item": 0})
			item_list.append(
				{
					"item_code": item,
					"qty": 1,
					"rate": rate,
					"is_alternative": "Alt" in item,
				}
			)

		quotation = make_quotation(item_list=item_list, do_not_submit=1)

		self.assertEqual(quotation.items[1].amount, 120)

		quotation.items[1].qty = 2
		quotation.save()

		self.assertEqual(quotation.items[1].amount, 240)

	def test_alternative_items_sales_order_mapping_with_stock_items(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		frappe.flags.args = frappe._dict()
		item_list = []
		stock_items = {
			"_Test Simple Item 1": 100,
			"_Test Alt 1": 120,
			"_Test Alt 2": 110,
			"_Test Simple Item 2": 200,
		}

		for item, rate in stock_items.items():
			make_item(item, {"is_stock_item": 1})
			item_list.append(
				{
					"item_code": item,
					"qty": 1,
					"rate": rate,
					"is_alternative": bool("Alt" in item),
					"warehouse": "_Test Warehouse - _TC",
				}
			)

		quotation = make_quotation(item_list=item_list)

		frappe.flags.args.selected_items = [quotation.items[2]]
		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(sales_order.transaction_date, 10)
		sales_order.save()

		self.assertEqual(sales_order.items[0].item_code, "_Test Alt 2")
		self.assertEqual(sales_order.items[1].item_code, "_Test Simple Item 2")
		self.assertEqual(sales_order.net_total, 310)

		sales_order.submit()
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

	def test_uom_validation(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = "_Test Item FOR UOM Validation"
		make_item(item, {"is_stock_item": 1})

		if not frappe.db.exists("UOM", "lbs"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "lbs", "must_be_whole_number": 1}).insert()
		else:
			frappe.db.set_value("UOM", "lbs", "must_be_whole_number", 1)

		quotation = make_quotation(item_code=item, qty=1, rate=100, do_not_submit=1)
		quotation.items[0].uom = "lbs"
		quotation.items[0].conversion_factor = 2.23
		self.assertRaises(frappe.ValidationError, quotation.save)

	def test_item_tax_template_for_quotation(self):
		from erpnext.stock.doctype.item.test_item import make_item

		if not frappe.db.exists("Account", {"account_name": "_Test Vat", "company": "_Test Company"}):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "_Test Vat",
					"company": "_Test Company",
					"account_type": "Tax",
					"root_type": "Asset",
					"is_group": 0,
					"parent_account": "Tax Assets - _TC",
					"tax_rate": 10,
				}
			).insert()

		if not frappe.db.exists("Item Tax Template", "Vat Template - _TC"):
			frappe.get_doc(
				{
					"doctype": "Item Tax Template",
					"name": "Vat Template",
					"title": "Vat Template",
					"company": "_Test Company",
					"taxes": [
						{
							"tax_type": "_Test Vat - _TC",
							"tax_rate": 5,
						}
					],
				}
			).insert()

		item_doc = make_item("_Test Item Tax Template QTN", {"is_stock_item": 1})
		if not frappe.db.exists(
			"Item Tax", {"parent": item_doc.name, "item_tax_template": "Vat Template - _TC"}
		):
			item_doc.append("taxes", {"item_tax_template": "Vat Template - _TC"})
			item_doc.save()

		quotation = make_quotation(item_code="_Test Item Tax Template QTN", qty=1, rate=100, do_not_submit=1)
		self.assertFalse(quotation.taxes)

		quotation.append_taxes_from_item_tax_template()
		quotation.save()
		self.assertTrue(quotation.taxes)
		for row in quotation.taxes:
			self.assertEqual(row.account_head, "_Test Vat - _TC")
			self.assertAlmostEqual(row.base_tax_amount, quotation.total * 5 / 100)

		item_doc.taxes = []
		item_doc.save()

	def test_grand_total_and_rounded_total_values(self):
		quotation = make_quotation(qty=6, rate=12.3, do_not_submit=1)

		self.assertEqual(quotation.grand_total, 73.8)
		self.assertEqual(quotation.rounding_adjustment, 0.2)
		self.assertEqual(quotation.rounded_total, 74)

		quotation.disable_rounded_total = 1
		quotation.save()

		self.assertEqual(quotation.grand_total, 73.8)
		self.assertEqual(quotation.rounding_adjustment, 0)
		self.assertEqual(quotation.rounded_total, 0)


test_records = frappe.get_test_records("Quotation")


def enable_calculate_bundle_price(enable=1):
	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.editable_bundle_item_rates = enable
	selling_settings.save()


def get_quotation_dict(party_name=None, item_code=None):
	if not party_name:
		party_name = "_Test Customer"
	if not item_code:
		item_code = "_Test Item"

	return {
		"doctype": "Quotation",
		"party_name": party_name,
		"items": [{"item_code": item_code, "qty": 1, "rate": 100}],
	}


def make_quotation(**args):
	qo = frappe.new_doc("Quotation")
	args = frappe._dict(args)
	if args.transaction_date:
		qo.transaction_date = args.transaction_date

	qo.company = args.company or "_Test Company"
	qo.party_name = args.party_name or "_Test Customer"
	qo.currency = args.currency or "INR"
	if args.selling_price_list:
		qo.selling_price_list = args.selling_price_list

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			qo.append("items", item)

	else:
		qo.append(
			"items",
			{
				"item_code": args.item or args.item_code or "_Test Item",
				"warehouse": args.warehouse,
				"qty": args.qty or 10,
				"uom": args.uom or None,
				"rate": args.rate or 100,
			},
		)

	if not args.do_not_save:
		qo.insert()
		if not args.do_not_submit:
			qo.submit()

	return qo
