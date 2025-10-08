# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import add_days, add_months, flt, getdate, nowdate

from erpnext.controllers.accounts_controller import InvalidQtyError
from erpnext.selling.doctype.quotation.quotation import make_sales_order
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

test_dependencies = ["Product Bundle"]


class TestQuotation(FrappeTestCase):
	def test_quotation_qty(self):
		qo = make_quotation(qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			qo.save()

		# No error with qty=1
		qo.items[0].qty = 1
		qo.save()
		self.assertEqual(qo.items[0].qty, 1)

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

	def test_do_not_add_ordered_items_in_new_sales_order(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item("_Test Item for Quotation for SO", {"is_stock_item": 1})
		quotation = make_quotation(qty=5, do_not_submit=True)
		quotation.append(
			"items",
			{
				"item_code": item.name,
				"qty": 5,
				"rate": 100,
				"conversion_factor": 1,
				"uom": item.stock_uom,
				"warehouse": "_Test Warehouse - _TC",
				"stock_uom": item.stock_uom,
			},
		)
		quotation.submit()
		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		self.assertEqual(len(sales_order.items), 2)
		sales_order.remove(sales_order.items[1])
		sales_order.submit()
		sales_order = make_sales_order(quotation.name)
		self.assertEqual(len(sales_order.items), 1)
		self.assertEqual(sales_order.items[0].item_code, item.name)
		self.assertEqual(sales_order.items[0].qty, 5.0)

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

	@change_settings("Selling Settings", {"allow_zero_qty_in_quotation": 1})
	def test_so_from_zero_qty_quotation(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Item 2", {"is_stock_item": 1})
		quotation = make_quotation(qty=0, do_not_save=1)
		quotation.append("items", {"item_code": "_Test Item 2", "qty": 10, "rate": 100})
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		self.assertEqual(sales_order.items[0].qty, 0)
		self.assertEqual(sales_order.items[1].qty, 10)

		sales_order.items[0].qty = 10
		sales_order.items[1].qty = 5
		sales_order.submit()

		quotation.reload()
		self.assertEqual(quotation.status, "Partially Ordered")

		sales_order_2 = make_sales_order(quotation.name)
		sales_order_2.delivery_date = nowdate()
		self.assertEqual(sales_order_2.items[0].qty, 0)
		self.assertEqual(sales_order_2.items[1].qty, 5)

		del sales_order_2.items[0]
		sales_order_2.submit()

		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

	def test_duplicate_items_in_quotation(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.stock.doctype.item.test_item import make_item

		# item code same but description different
		make_item("_Test Item 2", {"is_stock_item": 1})

		quotation = make_quotation(qty=1, rate=100, do_not_submit=1)

		# duplicate items
		for qty in [1, 1, 2, 3]:
			quotation.append("items", {"item_code": "_Test Item", "qty": qty, "rate": 100})

		quotation.append("items", {"item_code": "_Test Item 2", "qty": 5, "rate": 100})

		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()

		self.assertEqual(len(sales_order.items), 6)
		self.assertEqual(sales_order.items[0].qty, 1)
		self.assertEqual(sales_order.items[-1].qty, 5)

		# Row 1: 10, Row 4: 1, Row 5: 1
		sales_order.items[0].qty = 10
		sales_order.items[3].qty = 1
		sales_order.items[4].qty = 1
		sales_order.submit()

		quotation.reload()
		self.assertEqual(quotation.status, "Partially Ordered")

		sales_order_2 = make_sales_order(quotation.name)
		sales_order_2.delivery_date = nowdate()
		self.assertEqual(len(sales_order_2.items), 2)
		self.assertEqual(sales_order_2.items[0].qty, 1)
		self.assertEqual(sales_order_2.items[1].qty, 2)

		self.assertEqual(sales_order_2.items[0].quotation_item, quotation.items[3].name)
		self.assertEqual(sales_order_2.items[1].quotation_item, quotation.items[4].name)

		sales_order_2.submit()
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

	def test_quotation_to_sales_invoice_with_sr_TC_S_030(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, rate=4000)
		quotation = make_quotation(
			party_name="_Test Customer",
			company="_Test Company",
			cost_center="Main - _TC",
			item="_Test Item Home Desktop 100",
			qty=4,
			rate=5000,
			warehouse="Stores - _TC",
			currency="INR",
			selling_price_list="Standard Selling",
			shipping_rule="_Test Shipping Rule",
			update_stock=1,
			do_not_submit=True,
		)
		quotation.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": "_Test Account Shipping Charges - _TC",
				"cost_center": "Main - _TC",
				"rate": 0,
				"tax_amount": 200,
				"description": "Shipping Charges",
			},
		)
		quotation.save()
		quotation.submit()
		self.assertEqual(quotation.status, "Open")
		self.assertEqual(quotation.grand_total, 20200)

		sales_order = make_sales_order(quotation.name)
		sales_order.update_stock = 1
		sales_order.delivery_date = add_days(nowdate(), 5)

		sales_order.insert()
		sales_order.submit()

		self.assertEqual(sales_order.status, "To Deliver and Bill")
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.insert()
		delivery_note.submit()

		self.assertEqual(delivery_note.status, "To Bill")
		for item in delivery_note.items:
			actual_qty = frappe.db.get_value(
				"Bin", {"item_code": item.item_code, "warehouse": item.warehouse}, "actual_qty"
			)
			expected_qty = item.actual_qty - item.qty
			self.assertEqual(actual_qty, expected_qty)

		sales_invoice = make_sales_invoice(delivery_note.name)
		sales_invoice.insert()
		sales_invoice.submit()

		sales_order.reload()
		delivery_note.reload()
		sales_order.reload()
		self.assertEqual(sales_invoice.status, "Unpaid")
		self.assertEqual(delivery_note.status, "Completed")
		self.assertEqual(sales_order.status, "Completed")

		debtor_account = frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		sales_account = frappe.db.get_value("Company", "_Test Company", "default_income_account")
		shipping_account = frappe.db.get_value("Shipping Rule", "_Test Shipping Rule", "account")

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": sales_invoice.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		self.assertAlmostEqual(gl_debits[debtor_account], 20200)
		self.assertAlmostEqual(gl_credits[sales_account], 20000)
		self.assertAlmostEqual(gl_credits[shipping_account], 200)
		shipping_rule_amount = frappe.db.get_value(
			"Sales Taxes and Charges",
			{"parent": sales_invoice.name, "account_head": shipping_account},
			"tax_amount",
		)
		self.assertAlmostEqual(shipping_rule_amount, 200)

	def test_quotation_to_sales_invoice_TC_S_075(self):
		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		delivery_note = self.create_and_submit_delivery_note(sales_order.name)
		self.stock_check(voucher=delivery_note.name, qty=-4)

		self.assertEqual(delivery_note.status, "To Bill")

		sales_invoice = self.create_and_submit_sales_invoice(delivery_note.name, expected_amount=20000)
		self.assertEqual(sales_invoice.status, "Unpaid")

		delivery_note.reload()
		sales_order.reload()
		self.assertEqual(delivery_note.status, "Completed")
		self.assertEqual(sales_order.status, "Completed")

	def test_quotation_to_sales_invoice_with_double_entries_TC_S_076(self):
		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")

		# First Sales Order
		sales_order_1 = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5), qty=2)
		quotation.reload()
		self.assertEqual(quotation.status, "Partially Ordered")

		delivery_note_1 = self.create_and_submit_delivery_note(sales_order_1.name)
		self.stock_check(voucher=delivery_note_1.name, qty=-2)

		self.assertEqual(delivery_note_1.status, "To Bill")

		self.create_and_submit_sales_invoice(delivery_note_1.name, expected_amount=10000)

		# Second Sales Order
		sales_order_2 = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5), qty=2)
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		delivery_note_2 = self.create_and_submit_delivery_note(sales_order_2.name)
		self.stock_check(voucher=delivery_note_2.name, qty=-2)

		self.assertEqual(delivery_note_2.status, "To Bill")

		self.create_and_submit_sales_invoice(delivery_note_2.name, expected_amount=10000)

	def test_quotation_to_sales_invoice_with_double_entries_DN_SI_TC_S_077(self):
		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		# First Delivery Note and Sales Invoice
		delivery_note_1 = self.create_and_submit_delivery_note(sales_order.name, qty=2)
		self.stock_check(voucher=delivery_note_1.name, qty=-2)

		self.create_and_submit_sales_invoice(delivery_note_1.name, expected_amount=10000)

		# Second Delivery Note and Sales Invoice
		delivery_note_2 = self.create_and_submit_delivery_note(sales_order.name, qty=2)
		self.stock_check(voucher=delivery_note_2.name, qty=-2)

		self.create_and_submit_sales_invoice(delivery_note_2.name, expected_amount=10000)

		sales_order.reload()
		self.assertEqual(sales_order.status, "Completed")

	def test_quotation_to_sales_invoice_with_double_entries_SI_TC_S_078(self):
		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		# Delivery Note
		delivery_note = self.create_and_submit_delivery_note(sales_order.name)
		self.stock_check(voucher=delivery_note.name, qty=-4)

		# First Sales Invoice
		self.create_and_submit_sales_invoice(delivery_note.name, qty=2, expected_amount=10000)

		# Second Sales Invoice
		self.create_and_submit_sales_invoice(delivery_note.name, qty=2, expected_amount=10000)

		delivery_note.reload()
		sales_order.reload()
		self.assertEqual(delivery_note.status, "Completed")
		self.assertEqual(sales_order.status, "Completed")

	def test_quotation_to_sales_invoice_with_payment_entry_TC_S_079(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 1, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		self.create_and_submit_payment_entry(dt="Sales Order", dn=sales_order.name)

		delivery_note = self.create_and_submit_delivery_note(sales_order.name)
		self.stock_check(voucher=delivery_note.name, qty=-1)
		sales_invoice = self.create_and_submit_sales_invoice(
			delivery_note.name, advances_automatically=1, expected_amount=5000
		)
		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Paid")

	def test_quotation_to_sales_invoice_with_partially_payment_entry_TC_S_080(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_fiscal_year
		from erpnext.stock.doctype.item.test_item import create_item

		create_company("_Test Company")
		create_item(
			item_code="_Test Item Home Desktop 100",
			valuation_rate=100,
			warehouse="Stores - _TC",
			company="_Test Company",
			is_stock_item=1,
		)
		create_fiscal_year("_Test Company")
		create_customer()
		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 1, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		self.create_and_submit_payment_entry(dt="Sales Order", dn=sales_order.name, amt=2000)

		delivery_note = self.create_and_submit_delivery_note(sales_order.name)
		self.stock_check(voucher=delivery_note.name, qty=-1)
		sales_invoice = self.create_and_submit_sales_invoice(
			delivery_note.name, advances_automatically=1, expected_amount=5900
		)
		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Partly Paid")

		self.create_and_submit_payment_entry(dt="Sales Invoice", dn=sales_invoice.name)

		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Paid")

	def test_quotation_to_sales_invoice_with_update_stock_TC_S_081(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.update_stock = 1
		sales_invoice.save()
		sales_invoice.submit()

		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Unpaid")

		self.stock_check(voucher=sales_invoice.name, qty=-4)
		self.validate_gl_entries(voucher_no=sales_invoice.name, amount=20000)
		sales_order.reload()
		self.assertEqual(sales_order.status, "Completed")

	def test_quotation_to_sales_invoice_to_delivery_note_TC_S_082(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.save()
		sales_invoice.submit()

		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Unpaid")

		self.validate_gl_entries(voucher_no=sales_invoice.name, amount=20000)

		dn = make_delivery_note(sales_invoice.name)
		dn.insert()
		dn.submit()
		self.assertEqual(dn.status, "Completed")

		self.stock_check(voucher=dn.name, qty=-4)

	def test_quotation_to_sales_invoice_to_with_2_delivery_note_TC_S_083(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
		from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")

		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.save()
		sales_invoice.submit()

		sales_invoice.reload()
		self.assertEqual(sales_invoice.status, "Unpaid")

		self.validate_gl_entries(voucher_no=sales_invoice.name, amount=20000)

		dn_1 = make_delivery_note(sales_invoice.name)
		dn_1.insert()
		for i in dn_1.items:
			i.qty = 2
		dn_1.save()
		dn_1.submit()
		self.stock_check(voucher=dn_1.name, qty=-2)
		self.assertEqual(dn_1.status, "Completed")

		dn_2 = make_delivery_note(sales_invoice.name)
		dn_2.insert()
		for i in dn_2.items:
			i.qty = 2
		dn_2.save()
		dn_2.submit()
		self.stock_check(voucher=dn_2.name, qty=-2)
		self.assertEqual(dn_2.status, "Completed")

	def test_quotation_to_material_request_TC_S_084(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_material_request

		quotation = self.create_and_submit_quotation("_Test Item Home Desktop 100", 4, 5000, "Stores - _TC")
		sales_order = self.create_and_submit_sales_order(quotation.name, add_days(nowdate(), 5))
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")
		mr = make_material_request(sales_order.name)
		mr.schedule_date = nowdate()
		mr.save()
		mr.submit()
		mr.reload()
		self.assertEqual(mr.status, "Pending")

	def test_quotation_to_po_with_drop_ship_TC_S_111(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})
		so_items = [
			{
				"item_code": "_Test Item for Drop Shipping",
				"warehouse": "",
				"qty": 2,
				"rate": 5000,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		quotation = self.create_and_submit_quotation("_Test Item for Drop Shipping", 1, 5000, "Stores - _TC")

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(nowdate(), 5)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.supplier = "_Test Supplier"
		sales_order.save()
		sales_order.submit()

		quotation.reload()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		self.assertEqual(quotation.status, "Ordered")

		purchase_orders = make_purchase_order_for_default_supplier(sales_order.name, selected_items=so_items)
		for i in purchase_orders[0].items:
			i.rate = 3000
		purchase_orders[0].submit()

		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

	@if_app_installed("india_compliance")
	def test_quotation_to_po_with_drop_ship_with_GST_TC_S_112(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order_for_default_supplier
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			create_test_tax_data,
			test_item_tax_template,
		)
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})
		so_items = [
			{
				"item_code": "_Test Item for Drop Shipping",
				"warehouse": "",
				"qty": 2,
				"rate": 5000,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 18% - _TC"):
			test_item_tax_template(company="_Test Company", gst_rate=18, title="GST 18%")

		quotation = make_quotation(
			item="_Test Item for Drop Shipping", qty=1, rate=5000, warehouse="Stores - _TC", do_not_save=1
		)
		for i in quotation.items:
			i.item_tax_template = "GST 18% - _TC"
		quotation.tax_category = "In-State"
		quotation.taxes_and_charges = "Output GST In-state - _TC"
		quotation.save()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(nowdate(), 5)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.item_tax_template = "GST 18% - _TC"
			i.supplier = "_Test Supplier"
		sales_order.tax_category = "In-State"
		sales_order.taxes_and_charges = "Output GST In-state - _TC"
		sales_order.save()
		sales_order.submit()

		quotation.reload()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		self.assertEqual(quotation.status, "Ordered")

		purchase_orders = make_purchase_order_for_default_supplier(sales_order.name, selected_items=so_items)
		for i in purchase_orders[0].items:
			i.rate = 3000
			i.item_tax_template = "GST 18% - _TC"
		purchase_orders[0].tax_category = "In-State"
		purchase_orders[0].taxes_and_charges = "Input GST In-state - _TC"
		purchase_orders[0].save()
		purchase_orders[0].submit()
		self.assertAlmostEqual(purchase_orders[0].grand_total, 3540)
		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

	@if_app_installed("sales_commission")
	def test_quotation_to_si_with_pi_and_drop_ship_TC_S_114(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as make_pi_from_po,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_purchase_order_for_default_supplier,
			make_sales_invoice,
		)
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})
		so_items = [
			{
				"item_code": "_Test Item for Drop Shipping",
				"warehouse": "",
				"qty": 2,
				"rate": 5000,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		quotation = self.create_and_submit_quotation("_Test Item for Drop Shipping", 1, 5000, "Stores - _TC")

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(nowdate(), 5)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.supplier = "_Test Supplier"
		sales_order.save()
		sales_order.submit()

		quotation.reload()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		self.assertEqual(quotation.status, "Ordered")

		purchase_orders = make_purchase_order_for_default_supplier(sales_order.name, selected_items=so_items)
		for po in purchase_orders:
			po.currency = "INR"
			for i in po.items:
				i.rate = 3000
			po.save()
			po.submit()

		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

		pi = make_pi_from_po(purchase_orders[0].name)
		pi.currency = "INR"
		pi.save()
		pi.submit()

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertAlmostEqual(gl_debits["Cost of Goods Sold - _TC"], 3000)
		self.assertAlmostEqual(gl_credits["Creditors - _TC"], 3000)
		self.assertEqual(pi.status, "Unpaid")

		si = make_sales_invoice(sales_order.name)
		si.currency = "INR"
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		self.validate_gl_entries(voucher_no=si.name, amount=5000)

	@if_app_installed("india_compliance")
	def test_quotation_to_si_with_pi_and_drop_ship_with_GST_TC_S_116(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import (
			make_purchase_invoice as make_pi_from_po,
		)
		from erpnext.buying.doctype.purchase_order.purchase_order import update_status
		from erpnext.selling.doctype.sales_order.sales_order import (
			make_purchase_order_for_default_supplier,
			make_sales_invoice,
		)
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			create_test_tax_data,
			test_item_tax_template,
		)
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Item for Drop Shipping", {"is_stock_item": 1, "delivered_by_supplier": 1})
		so_items = [
			{
				"item_code": "_Test Item for Drop Shipping",
				"warehouse": "",
				"qty": 2,
				"rate": 5000,
				"delivered_by_supplier": 1,
				"supplier": "_Test Supplier",
			}
		]

		create_test_tax_data()
		if not frappe.db.exists("Item Tax Template", "GST 18% - _TC"):
			test_item_tax_template(company="_Test Company", gst_rate=18, title="GST 18%")

		quotation = make_quotation(
			item="_Test Item for Drop Shipping", qty=1, rate=5000, warehouse="Stores - _TC", do_not_save=1
		)
		for i in quotation.items:
			i.item_tax_template = "GST 18% - _TC"
		quotation.tax_category = "In-State"
		quotation.taxes_and_charges = "Output GST In-state - _TC"
		quotation.save()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = add_days(nowdate(), 5)
		for i in sales_order.items:
			i.delivered_by_supplier = 1
			i.item_tax_template = "GST 18% - _TC"
			i.supplier = "_Test Supplier"
		sales_order.tax_category = "In-State"
		sales_order.taxes_and_charges = "Output GST In-state - _TC"
		sales_order.save()
		sales_order.submit()

		quotation.reload()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		self.assertEqual(quotation.status, "Ordered")

		purchase_orders = make_purchase_order_for_default_supplier(sales_order.name, selected_items=so_items)
		for i in purchase_orders[0].items:
			i.rate = 3000
			i.item_tax_template = "GST 18% - _TC"
		purchase_orders[0].tax_category = "In-State"
		purchase_orders[0].currency = "INR"
		purchase_orders[0].taxes_and_charges = "Input GST In-state - _TC"
		purchase_orders[0].save()
		purchase_orders[0].submit()

		update_status("Delivered", purchase_orders[0].name)
		sales_order.reload()
		purchase_orders[0].reload()
		self.assertEqual(sales_order.status, "To Bill")
		self.assertEqual(purchase_orders[0].status, "Delivered")

		pi = make_pi_from_po(purchase_orders[0].name)
		pi.save()
		pi.submit()

		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertAlmostEqual(gl_debits["Cost of Goods Sold - _TC"], 3000)
		self.assertAlmostEqual(gl_debits["Input Tax SGST - _TC"], 270)
		self.assertAlmostEqual(gl_debits["Input Tax CGST - _TC"], 270)
		self.assertAlmostEqual(gl_credits["Creditors - _TC"], 3540)
		self.assertEqual(pi.status, "Unpaid")

		si = make_sales_invoice(sales_order.name)
		si.save()
		si.submit()

		self.assertEqual(si.status, "Unpaid")
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": si.name}, fields=["account", "debit", "credit"]
		)
		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}
		self.assertAlmostEqual(gl_debits["Debtors - _TC"], 5900)
		self.assertAlmostEqual(gl_credits["Output Tax SGST - _TC"], 450)
		self.assertAlmostEqual(gl_credits["Output Tax CGST - _TC"], 450)
		self.assertAlmostEqual(gl_credits["Sales - _TC"], 5000)

	def test_quotation_expired_to_create_sales_order_TC_S_153(self):
		selling_setting = frappe.get_doc("Stock Settings")
		selling_setting.allow_sales_order_creation_for_expired_quotation = 1
		selling_setting.save()

		quotation = make_quotation(qty=1, rate=100, transaction_date=add_days(nowdate(), -1), do_not_submit=1)
		quotation.submit()

		self.assertEqual(quotation.grand_total, 100)
		self.assertEqual(quotation.status, "Open")

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		sales_order.set("payment_schedule", [])
		sales_order.save()
		sales_order.submit()

		self.assertEqual(sales_order.status, "To Deliver and Bill")

	def test_set_indicator_on_quotation_TC_S_170(self):
		doc = frappe.copy_doc(test_records[0])
		doc.save()

		doc.docstatus = 1
		doc.valid_till = add_days(nowdate(), 5)
		doc.set_indicator()
		self.assertEqual(doc.indicator_color, "blue")
		self.assertEqual(doc.indicator_title, "Submitted")

		doc.valid_till = add_days(nowdate(), -1)
		doc.set_indicator()
		self.assertEqual(doc.indicator_color, "gray")
		self.assertEqual(doc.indicator_title, "Expired")

	@if_app_installed("erpnext_crm")
	def test_lead_to_quotation_TC_S_171(self):
		from erpnext_crm.erpnext_crm.doctype.lead.lead import make_opportunity
		from erpnext_crm.erpnext_crm.doctype.lead.test_lead import make_lead
		from erpnext_crm.erpnext_crm.doctype.opportunity.opportunity import make_quotation

		if not frappe.db.exists(
			"Quotation Lost Reason", {"order_lost_reason": "_Test Quotation Lost Reason"}
		):
			frappe.get_doc(
				{"doctype": "Quotation Lost Reason", "order_lost_reason": "_Test Quotation Lost Reason"}
			).insert()

		if not frappe.db.exists("Competitor", {"competitor_name": "_Test Competitors"}):
			frappe.get_doc({"doctype": "Competitor", "competitor_name": "_Test Competitors"}).insert()
		if not frappe.db.exists("Tax Category", "In-State"):
			frappe.get_doc({"doctype": "Tax Category", "title": "In-State"}).insert()

		if not frappe.db.exists("Sales Taxes and Charges Template", "Output GST In-state - _TC"):
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Output GST In-state",
					"company": "_Test Company",
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": "Output Tax SGST - _TC",
							"rate": 9,
							"description": "SGST - _TC",
						},
						{
							"charge_type": "On Net Total",
							"account_head": "Output Tax CGST - _TC",
							"rate": 9,
							"description": "CGST - _TC",
						},
					],
				}
			).insert()

		lead = make_lead()
		lead.company = "_Test Company"
		lead.save()

		opportunity = make_opportunity(lead.name)
		opportunity.opportunity_type = ""
		opportunity.sales_stage = ""
		opportunity.company = "_Test Company"
		opportunity.save()

		quotation = make_quotation(opportunity.name)
		quotation.company = "_Test Company"
		quotation.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"prevdoc_doctype": "Opportunity",
				"prevdoc_docname": opportunity.name,
			},
		)
		quotation.tax_category = "In-State"
		quotation.taxes_and_charges = "Output GST In-state - _TC"
		quotation.print_other_charges(quotation.name)
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.save()

		quotation.declare_enquiry_lost(
			[{"lost_reason": "_Test Quotation Lost Reason"}],
			[{"competitor": "_Test Competitors"}],
			"Test quotation Lost",
		)
		quotation.submit()
		opportunity.reload()
		lead.reload()

		self.assertEqual(lead.status, "Lost Quotation")
		self.assertEqual(opportunity.status, "Lost")
		self.assertEqual(quotation.status, "Lost")

		quotation.cancel()
		opportunity.reload()
		lead.reload()

		self.assertEqual(lead.status, "Opportunity")
		self.assertEqual(opportunity.status, "Open")
		self.assertEqual(quotation.status, "Cancelled")

	@if_app_installed("sales_commission")
	def test_quotation_with_referral_sales_partner_TC_S_172(self):
		if not frappe.db.exists("Sales Partner", "_Test Sales Partner"):
			frappe.get_doc(
				{"doctype": "Sales Partner", "partner_name": "_Test Sales Partner", "commission_rate": 10}
			).insert()

		if not frappe.db.exists("Sales Person", "_Test Sales Person"):
			frappe.get_doc({"doctype": "Sales Person", "sales_person_name": "_Test Sales Person"}).insert()

		if not frappe.db.exists("Customer", "_Test Customer With Sales Team"):
			customer = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "_Test Customer With Sales Team",
					"customer_type": "Company",
					"sales_team": [
						{
							"sales_person": "_Test Sales Person",
							"allocated_percentage": 100,
							"commission_rate": 10,
						}
					],
				}
			).insert()
		else:
			customer = frappe.get_doc("Customer", "_Test Customer With Sales Team")

		quotation = make_quotation(customer=customer.name, do_not_save=1)
		quotation.referral_sales_partner = "_Test Sales Partner"
		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.save()
		quotation.submit()

		self.assertEqual(quotation.status, "Open")
		self.assertEqual(quotation.referral_sales_partner, "_Test Sales Partner")
		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		sales_order.run_method("set_missing_values")
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		self.assertEqual(sales_order.sales_partner, "_Test Sales Partner")

	@if_app_installed("erpnext_crm")
	def test_sales_invoice_flow_TC_S_179(self):
		from erpnext_crm.erpnext_crm.doctype.lead.lead import make_opportunity
		from erpnext_crm.erpnext_crm.doctype.lead.test_lead import make_lead
		from erpnext_crm.erpnext_crm.doctype.opportunity.opportunity import make_quotation

		from erpnext.selling.doctype.quotation.quotation import make_sales_invoice

		if not frappe.db.exists("Tax Category", "In-State"):
			frappe.get_doc({"doctype": "Tax Category", "title": "In-State"}).insert()

		if not frappe.db.exists("Sales Taxes and Charges Template", "Output GST In-state - _TC"):
			frappe.get_doc(
				{
					"doctype": "Sales Taxes and Charges Template",
					"title": "Output GST In-state",
					"company": "_Test Company",
					"taxes": [
						{
							"charge_type": "On Net Total",
							"account_head": "Output Tax SGST - _TC",
							"rate": 9,
							"description": "SGST - _TC",
						},
						{
							"charge_type": "On Net Total",
							"account_head": "Output Tax CGST - _TC",
							"rate": 9,
							"description": "CGST - _TC",
						},
					],
				}
			).insert()

		lead = make_lead()
		lead.email_id = ""
		lead.company = "_Test Company"
		lead.save()

		opportunity = make_opportunity(lead.name)
		opportunity.opportunity_type = ""
		opportunity.sales_stage = ""
		opportunity.company = "_Test Company"
		opportunity.save()

		quotation = make_quotation(opportunity.name)
		quotation.company = "_Test Company"
		quotation.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 5,
				"prevdoc_doctype": "Opportunity",
				"prevdoc_docname": opportunity.name,
			},
		)
		quotation.tax_category = "In-State"
		quotation.taxes_and_charges = "Output GST In-state - _TC"
		quotation.save()
		quotation.submit()

		charges = quotation.print_other_charges(quotation.name)
		self.assertEqual(len(charges), 2)

		invoice = make_sales_invoice(quotation.name)
		self.assertEqual(invoice.items[0].stock_qty, 5.0)

	@if_app_installed("erpnext_crm")
	def test_customer_from_prospect_TC_S_180(self):
		from erpnext_crm.erpnext_crm.doctype.lead.lead import make_opportunity
		from erpnext_crm.erpnext_crm.doctype.lead.test_lead import make_lead
		from erpnext_crm.erpnext_crm.doctype.opportunity.opportunity import make_quotation
		from erpnext_crm.erpnext_crm.doctype.prospect.test_prospect import add_lead_to_prospect, make_prospect

		lead = make_lead()
		lead.email_id = ""
		lead.company = "_Test Company"
		lead.save()

		prospect_doc = make_prospect()
		add_lead_to_prospect(lead.name, prospect_doc.name)
		prospect_doc.reload()
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Test Prospect Contact",
				"links": [
					{"link_doctype": "Prospect", "link_name": prospect_doc.name},
					{"link_doctype": "Lead", "link_name": lead.name},
				],
			}
		)
		contact.insert()

		opportunity = make_opportunity(lead.name)
		opportunity.opportunity_from = "Prospect"
		opportunity.party_name = prospect_doc.name
		opportunity.opportunity_type = ""
		opportunity.sales_stage = ""
		opportunity.company = "_Test Company"
		opportunity.save()

		quotation = make_quotation(opportunity.name)
		quotation.company = "_Test Company"
		quotation.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 1,
				"prevdoc_doctype": "Opportunity",
				"prevdoc_docname": opportunity.name,
				"against_blanket_order": 1,
			},
		)
		quotation.save()
		quotation.submit()

		self.assertEqual(quotation.quotation_to, "Prospect")
		self.assertEqual(quotation.party_name, prospect_doc.name)

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		customer_name = frappe.db.get_value("Customer", {"name": opportunity.party_name})
		contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})
		contact.save()
		sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")

	def stock_check(self, voucher, qty):
		stock_entries = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": voucher, "warehouse": "Stores - _TC"},
			fields=["actual_qty"],
		)
		self.assertEqual(sum([entry.actual_qty for entry in stock_entries]), qty)

	def create_and_submit_quotation(self, item, qty, rate, warehouse):
		make_stock_entry(item=item, target=warehouse, qty=10, rate=4000)
		quotation = make_quotation(item=item, qty=qty, rate=rate, warehouse=warehouse)
		self.assertEqual(quotation.status, "Open")
		return quotation

	def create_and_submit_sales_order(self, quotation_name, delivery_date, qty=None):
		sales_order = make_sales_order(quotation_name)
		sales_order.delivery_date = delivery_date
		sales_order.insert()
		if qty:
			for item in sales_order.items:
				item.qty = qty
			sales_order.save()
		sales_order.submit()
		self.assertEqual(sales_order.status, "To Deliver and Bill")
		return sales_order

	def create_and_submit_delivery_note(self, sales_order_name, qty=None):
		delivery_note = make_delivery_note(sales_order_name)
		delivery_note.insert()
		if qty:
			for item in delivery_note.items:
				item.qty = qty
			delivery_note.save()
		delivery_note.submit()
		return delivery_note

	def create_and_submit_sales_invoice(
		self, delivery_note_name, qty=None, expected_amount=None, advances_automatically=None
	):
		sales_invoice = make_sales_invoice(delivery_note_name)
		sales_invoice.insert()
		if qty:
			for item in sales_invoice.items:
				item.qty = qty

		if advances_automatically:
			sales_invoice.allocate_advances_automatically = 1
			sales_invoice.only_include_allocated_payments = 1
		sales_invoice.save()
		sales_invoice.submit()
		if expected_amount:
			self.validate_gl_entries(sales_invoice.name, expected_amount)
		return sales_invoice

	def validate_gl_entries(self, voucher_no, amount):
		frappe.db.get_value("Company", "_Test Company", "default_receivable_account")
		frappe.db.get_value("Company", "_Test Company", "default_income_account")
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": voucher_no}, fields=["account", "debit", "credit"]
		)

		gl_debits = {entry.account: entry.debit for entry in gl_entries}
		gl_credits = {entry.account: entry.credit for entry in gl_entries}

		total_debits = sum(gl_debits.values())
		total_credits = sum(gl_credits.values())

		self.assertAlmostEqual(total_debits, amount)
		self.assertAlmostEqual(total_credits, amount)

	def create_and_submit_payment_entry(self, dt=None, dn=None, amt=None):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		payment_entry = get_payment_entry(dt=dt, dn=dn)
		payment_entry.insert()
		if amt:
			payment_entry.paid_amount = amt
			for i in payment_entry.references:
				i.allocated_amount = amt
		payment_entry.save()
		payment_entry.submit()

		self.assertEqual(payment_entry.status, "Submitted", "Payment Entry not created")
		debit_account = (
			frappe.db.get_value("Company", "_Test Company", "default_bank_account") or "Cash - _TC"
		)
		credit_account = (
			frappe.db.get_value("Company", "_Test Company", "default_advance_received_account")
			or "Debtors - _TC"
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": payment_entry.name, "account": credit_account}, "credit"
			),
			payment_entry.paid_amount,
		)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": payment_entry.name, "account": debit_account}, "debit"
			),
			payment_entry.paid_amount,
		)
		return payment_entry


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
	qo.shiping_rule = args.shiping_rule
	qo.currency = args.currency or "INR"
	if args.selling_price_list:
		qo.selling_price_list = args.selling_price_list

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			qo.append("items", item)

	else:
		hsn_code = frappe.db.get_value("Item", args.item_code, "gst_hsn_code")
		qo.append(
			"items",
			{
				"item_code": args.item or args.item_code or "_Test Item",
				"warehouse": args.warehouse,
				"qty": args.qty if args.qty is not None else 10,
				"uom": args.uom or None,
				"rate": args.rate or 100,
				"gst_hsn_code": hsn_code or "11112222",
			},
		)

	if not args.do_not_save:
		qo.insert()
		if not args.do_not_submit:
			qo.submit()

	return qo


def create_customer(customer_name="_Test Customer", currency=None):
	if not frappe.db.exists("Customer", customer_name):
		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.type = "Individual"

		if currency:
			customer.default_currency = currency
		customer.save()
		return customer.name
	else:
		return customer_name
