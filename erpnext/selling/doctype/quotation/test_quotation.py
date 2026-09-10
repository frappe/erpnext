# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import frappe
from frappe.share import add
from frappe.tests import change_settings
from frappe.utils import add_days, add_months, flt, getdate, nowdate
from freezegun import freeze_time

from erpnext.accounts.doctype.sales_invoice.mapper import make_sales_return
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate
from erpnext.crm.doctype.opportunity.mapper import make_quotation as make_opportunity_quotation
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
from erpnext.crm.report.campaign_efficiency.campaign_efficiency import get_lead_quotation_count
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.quotation.mapper import make_sales_invoice, make_sales_order
from erpnext.selling.doctype.quotation.quotation import Quotation, set_expired_status
from erpnext.selling.page.sales_funnel.sales_funnel import get_funnel_data
from erpnext.selling.report.quotation_trends.quotation_trends import execute as quotation_trends
from erpnext.selling.report.sales_analytics.sales_analytics import execute as sales_analytics
from erpnext.selling.report.territory_wise_sales.territory_wise_sales import execute as territory_sales
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestQuotation(ERPNextTestSuite):
	def setUp(self):
		# Keep default dates scoped to each test, including frozen report dates.
		self.enterContext(patch.object(frappe.local, "new_doc_templates", {}))
		self.load_test_records("Quotation")

	def test_update_child_quotation_add_item(self):
		item_1 = frappe.get_doc("Item", "_Test Item")
		item_2 = make_item("_Test Item 1")

		item_list = [
			{"item_code": item_1.item_code, "warehouse": "", "qty": 10, "rate": 300},
			{"item_code": item_2.item_code, "warehouse": "", "qty": 5, "rate": 400},
		]

		qo = make_quotation(item_list=item_list)
		first_item = qo.get("items")[0]
		second_item = qo.get("items")[1]
		trans_item = json.dumps(
			[
				{
					"item_code": first_item.item_code,
					"rate": first_item.rate,
					"qty": 11,
					"docname": first_item.name,
				},
				{
					"item_code": second_item.item_code,
					"rate": second_item.rate,
					"qty": second_item.qty,
					"docname": second_item.name,
					"description": "test",
				},
				{"item_code": "_Test Item 2", "rate": 100, "qty": 7},
			]
		)

		update_child_qty_rate("Quotation", trans_item, qo.name)
		qo.reload()
		self.assertEqual(qo.get("items")[0].qty, 11)
		self.assertEqual(qo.get("items")[-1].rate, 100)
		self.assertEqual(qo.get("items")[1].description, "test")

	def test_disallow_due_date_before_transaction_date(self):
		qo = make_quotation(qty=3, do_not_submit=1)
		qo.payment_schedule[0].due_date = add_days(qo.transaction_date, -2)
		self.assertRaises(frappe.ValidationError, qo.save)

	def test_update_child_rate_change(self):
		item_1 = frappe.get_doc("Item", "_Test Item")
		item_2 = make_item("_Test Item 1")

		item_list = [
			{"item_code": item_1.item_code, "warehouse": "_Test Warehouse - _TC", "qty": 10, "rate": 300},
			{"item_code": item_2.item_code, "warehouse": "_Test Warehouse - _TC", "qty": 5, "rate": 400},
		]

		qo = make_quotation(item_list=item_list)
		so = make_sales_order(qo.name, args={"filtered_children": [qo.items[0].name]})
		so.delivery_date = nowdate()
		so.submit()
		qo.reload()
		trans_item = json.dumps(
			[
				{
					"item_code": qo.items[0].item_code,
					"rate": 5000,
					"qty": qo.items[0].qty,
					"docname": qo.items[0].name,
				},
				{
					"item_code": qo.items[1].item_code,
					"rate": qo.items[1].rate,
					"qty": qo.items[1].qty,
					"docname": qo.items[1].name,
				},
			]
		)
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Quotation", trans_item, qo.name)
		trans_item = json.dumps(
			[
				{
					"item_code": qo.items[0].item_code,
					"rate": qo.items[0].rate,
					"qty": qo.items[0].qty,
					"docname": qo.items[0].name,
				},
				{
					"item_code": qo.items[1].item_code,
					"rate": 50,
					"qty": qo.items[1].qty,
					"docname": qo.items[1].name,
				},
			]
		)
		update_child_qty_rate("Quotation", trans_item, qo.name)
		qo.reload()
		self.assertEqual(qo.items[1].rate, 50)

	def test_update_child_removing_item(self):
		qo = make_quotation(qty=10)
		sales_order = make_sales_order(qo.name)
		sales_order.delivery_date = nowdate()

		trans_item = json.dumps(
			[
				{
					"item_code": qo.items[0].item_code,
					"rate": qo.items[0].rate,
					"qty": qo.items[0].qty,
					"docname": qo.items[0].name,
				},
				{"item_code": "_Test Item 2", "rate": 100, "qty": 7},
			]
		)

		update_child_qty_rate("Quotation", trans_item, qo.name)
		sales_order.submit()
		qo.reload()
		self.assertEqual(qo.status, "Partially Ordered")

		trans_item = json.dumps([{"item_code": "_Test Item 2", "rate": 100, "qty": 7}])

		# check if items having a sales order can be removed
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Quotation", trans_item, qo.name)

		trans_item = json.dumps(
			[
				{
					"item_code": qo.items[0].item_code,
					"rate": qo.items[0].rate,
					"qty": qo.items[0].qty,
					"docname": qo.items[0].name,
				}
			]
		)

		# remove item with no sales order
		update_child_qty_rate("Quotation", trans_item, qo.name)
		qo.reload()
		self.assertEqual(len(qo.get("items")), 1)

	def test_update_child_qty_with_uom_conversion_factor(self):
		item = make_item(uoms=[{"uom": "Box", "conversion_factor": 5}])
		quotation = make_quotation(item_code=item.item_code, qty=6, uom="Box", do_not_submit=1)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()
		sales_order.items[0].qty = 2
		sales_order.save()
		sales_order.submit()

		quotation.reload()
		self.assertEqual(quotation.items[0].ordered_qty, 10)

		def update_qty(qty, conversion_factor=None):
			item = quotation.items[0]
			trans_items = json.dumps(
				[
					{
						"item_code": item.item_code,
						"description": item.description,
						"rate": item.rate,
						"qty": qty,
						"uom": item.uom,
						"conversion_factor": conversion_factor or item.conversion_factor,
						"docname": item.name,
					}
				]
			)
			update_child_qty_rate("Quotation", trans_items, quotation.name)

		update_qty(5, conversion_factor=2)
		quotation.reload()
		self.assertEqual(quotation.items[0].conversion_factor, 2)
		self.assertEqual(quotation.items[0].stock_qty, 10)

		self.assertRaises(frappe.ValidationError, update_qty, 4)

	def test_quotation_qty(self):
		qo = make_quotation(qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			qo.save()

		# No error with qty=1
		qo.items[0].qty = 1
		qo.save()
		self.assertEqual(qo.items[0].qty, 1)

	def test_quotation_zero_qty(self):
		"""
		Test if Quote with zero qty (Unit Price Item) is conditionally allowed.
		"""
		qo = make_quotation(qty=0, do_not_save=True)
		with change_settings("Selling Settings", {"allow_zero_qty_in_quotation": 1}):
			qo.save()
			self.assertEqual(qo.items[0].qty, 0)

	def test_make_quotation_without_terms(self):
		quotation = make_quotation(do_not_save=1)
		self.assertFalse(quotation.get("payment_schedule"))

		quotation.insert()

		self.assertTrue(quotation.payment_schedule)

	def test_terms_attachments_are_copied_to_quotation(self):
		terms = make_terms_and_conditions(copy_attachments_to_transaction=True)
		first_attachment = make_file_attachment(
			"Terms and Conditions",
			terms.name,
			content="First terms attachment",
		)

		quotation = make_quotation(do_not_save=1)
		quotation.tc_name = terms.name
		quotation.insert()

		self.assertEqual(get_attachment_urls("Quotation", quotation.name), {first_attachment.file_url})

		second_attachment = make_file_attachment(
			"Terms and Conditions",
			terms.name,
			content="Second terms attachment",
		)
		quotation.valid_till = add_days(getdate(quotation.valid_till), 1)
		quotation.save()

		quotation_attachments = get_attachment_urls("Quotation", quotation.name)
		self.assertEqual(quotation_attachments, {first_attachment.file_url})
		self.assertNotIn(second_attachment.file_url, quotation_attachments)

		new_terms = make_terms_and_conditions(copy_attachments_to_transaction=True)
		new_terms_attachment = make_file_attachment(
			"Terms and Conditions",
			new_terms.name,
			content="Attachment from updated terms",
		)
		quotation.tc_name = new_terms.name
		quotation.valid_till = add_days(getdate(quotation.valid_till), 1)
		quotation.save()

		self.assertEqual(
			get_attachment_urls("Quotation", quotation.name),
			{first_attachment.file_url, new_terms_attachment.file_url},
		)

	def test_terms_attachments_are_not_copied_when_disabled(self):
		terms = make_terms_and_conditions(copy_attachments_to_transaction=False)
		make_file_attachment(
			"Terms and Conditions",
			terms.name,
			content="Terms attachment should stay on the template",
		)

		quotation = make_quotation(do_not_save=1)
		quotation.tc_name = terms.name
		quotation.insert()

		self.assertFalse(get_attachment_urls("Quotation", quotation.name))

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"automatically_fetch_payment_terms": 1},
	)
	def test_make_sales_order_terms_copied(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)

		self.assertTrue(sales_order.get("payment_schedule"))

	def test_do_not_add_ordered_items_in_new_sales_order(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

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
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		maintain_rate = frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate")
		frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", 1)

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.items[0].rate = 1
		self.assertRaises(frappe.ValidationError, sales_order.save)

		frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", maintain_rate)

	def test_make_sales_order_with_different_currency(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
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
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
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

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{
			"add_taxes_from_item_tax_template": 0,
			"add_taxes_from_taxes_and_charges_template": 0,
			"automatically_fetch_payment_terms": 1,
		},
	)
	def test_make_sales_order_with_terms(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.update({"payment_terms_template": "_Test Payment Term Template"})
		quotation.insert()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.save()
		quotation.submit()

		self.assertEqual(quotation.payment_schedule[0].payment_amount, 500.00)
		self.assertEqual(quotation.payment_schedule[0].due_date, quotation.transaction_date)
		self.assertEqual(quotation.payment_schedule[1].payment_amount, 500.00)
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

		self.assertEqual(sales_order.payment_schedule[0].payment_amount, 500.00)
		self.assertEqual(
			getdate(sales_order.payment_schedule[0].due_date), getdate(quotation.transaction_date)
		)
		self.assertEqual(sales_order.payment_schedule[1].payment_amount, 500.00)
		self.assertEqual(
			getdate(sales_order.payment_schedule[1].due_date),
			getdate(add_days(quotation.transaction_date, 30)),
		)

	def test_valid_till_before_transaction_date(self):
		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
		quotation.valid_till = add_days(quotation.transaction_date, -1)
		self.assertRaises(frappe.ValidationError, quotation.validate)

	def test_so_from_expired_quotation(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		frappe.db.set_single_value("Selling Settings", "allow_sales_order_creation_for_expired_quotation", 0)

		quotation = frappe.copy_doc(self.globalTestRecords["Quotation"][0])
		quotation.valid_till = add_days(nowdate(), -1)
		quotation.insert()
		quotation.submit()

		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)

		frappe.db.set_single_value("Selling Settings", "allow_sales_order_creation_for_expired_quotation", 1)

		make_sales_order(quotation.name)

	def test_create_quotation_with_margin(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order
		from erpnext.selling.doctype.sales_order.mapper import (
			make_delivery_note,
			make_sales_invoice,
		)

		rate_with_margin = flt((1500 * 18.75) / 100 + 1500)

		test_record = frappe.copy_doc(self.globalTestRecords["Quotation"][0])

		test_record.items[0].price_list_rate = 1500
		test_record.items[0].margin_type = "Percentage"
		test_record.items[0].margin_rate_or_amount = 18.75
		# set rate to zero, so that it is recalculated on save
		test_record.items[0].rate = 0

		quotation = frappe.copy_doc(test_record)
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
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

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
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

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
		item = "_Test Item FOR UOM Validation"
		make_item(item, {"is_stock_item": 1})

		quotation = make_quotation(item_code=item, qty=1, rate=100, do_not_submit=1)
		quotation.items[0].uom = "_Test UOM"
		quotation.items[0].conversion_factor = 2.23
		self.assertRaises(frappe.ValidationError, quotation.save)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"add_taxes_from_item_tax_template": 1, "add_taxes_from_taxes_and_charges_template": 0},
	)
	def test_item_tax_template_for_quotation(self):
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

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_zero_qty_in_quotation": 1})
	def test_so_from_zero_qty_quotation(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

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

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_duplicate_items_in_quotation(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		# item code same but description different
		quotation = make_quotation(qty=10, rate=100, do_not_submit=1)

		# duplicate items
		for qty in [1, 1, 2, 3]:
			quotation.append("items", {"item_code": "_Test Item", "qty": qty, "rate": 100})

		quotation.append("items", {"item_code": "_Test Item 2", "qty": 5, "rate": 100})

		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.delivery_date = nowdate()

		self.assertEqual(len(sales_order.items), 6)
		self.assertEqual(sales_order.items[0].qty, 10)
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

	@ERPNextTestSuite.change_settings("Accounts Settings", {"allow_pegged_currencies_exchange_rates": True})
	def test_make_quotation_qar_to_inr(self):
		quotation = make_quotation(
			currency="QAR",
			transaction_date="2026-01-01",
		)

		cache = frappe.cache()
		key = "currency_exchange_rate_{}:{}:{}".format("2026-01-01", "QAR", "INR")
		value = cache.get(key)
		expected_rate = flt(value) / 3.64

		self.assertEqual(
			quotation.conversion_rate,
			expected_rate,
			f"Expected conversion rate {expected_rate}, got {quotation.conversion_rate}",
		)

	def test_over_order_limit(self):
		quotation = make_quotation(qty=5)
		so1 = make_sales_order(quotation.name)
		so2 = make_sales_order(quotation.name)
		so1.delivery_date = nowdate()
		so2.delivery_date = nowdate()

		so1.submit()
		self.assertRaises(frappe.ValidationError, so2.submit)

	def test_quotation_status(self):
		quotation = make_quotation()

		so1 = make_sales_order(quotation.name)
		so1.delivery_date = nowdate()
		so1.submit()
		quotation.reload()
		self.assertEqual(quotation.status, "Ordered")
		so1.cancel()

		quotation.reload()
		self.assertEqual(quotation.status, "Open")

		so2 = make_sales_order(quotation.name)
		so2.delivery_date = nowdate()
		so2.items[0].qty = 1
		so2.submit()
		quotation.reload()
		self.assertEqual(quotation.status, "Partially Ordered")

		so2.cancel()

		quotation.reload()
		self.assertEqual(quotation.status, "Open")

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"automatically_fetch_payment_terms": 1},
	)
	def test_make_sales_order_with_payment_terms(self):
		from erpnext.selling.doctype.quotation.mapper import make_sales_order

		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template for Quotation",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 0,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 10,
					},
				],
			}
		).save()

		quotation = make_quotation(qty=10, rate=1000, do_not_submit=1)
		quotation.transaction_date = add_days(nowdate(), -2)
		quotation.valid_till = add_days(nowdate(), 10)
		quotation.update({"payment_terms_template": template.name, "payment_schedule": []})
		quotation.save()
		quotation.submit()

		self.assertEqual(quotation.payment_schedule[0].payment_amount, 5000)
		self.assertEqual(quotation.payment_schedule[1].payment_amount, 5000)
		self.assertEqual(quotation.payment_schedule[0].due_date, quotation.transaction_date)
		self.assertEqual(quotation.payment_schedule[1].due_date, add_days(quotation.transaction_date, 10))

		sales_order = make_sales_order(quotation.name)
		sales_order.transaction_date = nowdate()
		sales_order.delivery_date = nowdate()
		sales_order.save()

		self.assertEqual(sales_order.payment_schedule[0].due_date, sales_order.transaction_date)
		self.assertEqual(sales_order.payment_schedule[1].due_date, add_days(sales_order.transaction_date, 10))
		self.assertEqual(sales_order.payment_schedule[0].payment_amount, 5000)
		self.assertEqual(sales_order.payment_schedule[1].payment_amount, 5000)

	def test_create_revision_preserves_submitted_source(self):
		source = make_quotation(do_not_submit=True)
		self.assertRaises(frappe.ValidationError, source.make_revision)
		source.submit()
		draft = source.make_revision()
		self.assertTrue(draft.is_new())
		self.assertEqual(draft.docstatus, 0)
		for child in draft.get_all_children():
			self.assertFalse(child.parent)
		draft.insert()
		self.assertEqual(draft.name, f"{source.name}-REV-1")
		self.assertEqual(draft.original_quotation, source.name)
		self.assertEqual(draft.revised_from, source.name)
		self.assertEqual(draft.quotation_version, 1)
		self.assertEqual(draft.quote_revision_count, 0)
		self.assertEqual(draft.items[0].qty, source.items[0].qty)
		self.assertEqual(draft.items[0].rate, source.items[0].rate)
		self.assertNotEqual(draft.items[0].name, source.items[0].name)
		draft.items[0].qty += 1
		draft.items[0].rate += 10
		draft.save()
		self.assertEqual(draft.quote_revision_count, 1)
		source.reload()
		self.assertEqual(source.docstatus, 1)
		self.assertEqual(source.status, "Open")
		self.assertEqual(source.quote_revision_count, 0)
		self.assertNotEqual(source.items[0].qty, draft.items[0].qty)
		self.assertNotEqual(source.items[0].rate, draft.items[0].rate)

	def test_ordinary_duplicate_starts_new_family(self):
		source = make_quotation()
		version = source.make_revision().insert()
		duplicate = frappe.copy_doc(version, ignore_no_copy=False).insert()
		self.assertFalse(duplicate.original_quotation)
		self.assertFalse(duplicate.revised_from)
		self.assertEqual(duplicate.quotation_version, 0)
		self.assertEqual(duplicate.quote_revision_count, 0)
		self.assertNotIn("-REV-", duplicate.name)

	def test_revision_protects_party_lineage_and_counters(self):
		source = make_quotation()
		version = source.make_revision().insert()
		version.party_name = "_Test Customer 1"
		self.assertRaises(frappe.ValidationError, version.save)
		version.reload()
		payload = version.as_dict()
		payload.update(revision_fields=[], quotation_version=99)
		self.assertRaises(frappe.ValidationError, frappe.get_doc(payload).save)
		version.reload()
		payload = version.as_dict()
		payload.update(
			quote_revision_count=99,
			is_latest_revision=1,
			revision_commercial_fields=[],
			revision_item_fields=[],
			revision_tax_fields=[],
			revision_payment_fields=[],
		)
		version = frappe.get_doc(payload)
		version.save()
		self.assertEqual(version.quote_revision_count, 0)
		self.assertFalse(version.is_latest_revision)
		version.items[0].description = "Revised specification"
		version.save().reload()
		self.assertEqual(version.quote_revision_count, 1)
		source.is_latest_revision = 0
		source.save()
		self.assertTrue(source.is_latest_revision)

	def test_counter_tracks_commercial_changes(self):
		for field, value in (
			("qty", 12),
			("rate", 125),
			("discount_percentage", 5),
			("discount_amount", 5),
			("description", "Revised specification"),
			("additional_discount_percentage", 5),
		):
			with self.subTest(field=field):
				quotation = make_quotation(do_not_submit=True)
				if field.startswith("discount_"):
					quotation.items[0].price_list_rate = 100
					quotation.items[0].rate = 95
				target = quotation if field == "additional_discount_percentage" else quotation.items[0]
				target.set(field, value)
				quotation.save()
				self.assertEqual(quotation.quote_revision_count, 1)
				quotation.save()
				self.assertEqual(quotation.quote_revision_count, 1)

	def test_counter_ignores_noncommercial_changes_and_item_reordering(self):
		quotation = make_quotation(
			do_not_submit=True,
			item_list=[
				{"item_code": "_Test Item", "qty": 10, "rate": 100},
				{"item_code": "_Test Item 2", "qty": 1, "rate": 50},
			],
		)
		self.assertEqual(quotation.quote_revision_count, 0)
		quotation.save()
		self.assertEqual(quotation.quote_revision_count, 0)
		quotation.letter_head = None
		quotation.language = "en"
		quotation.items.reverse()
		for idx, item in enumerate(quotation.items, 1):
			item.idx = idx
		quotation.save()
		self.assertEqual(quotation.quote_revision_count, 0)
		quotation.submit().save()
		self.assertEqual(quotation.quote_revision_count, 0)

	def test_submitted_update_items_counts_once_and_retains_history(self):
		quotation = make_quotation()
		items = self.update_items_payload(quotation)
		items[0].update(qty=12, rate=125, description="New specification")
		with patch.object(frappe, "in_test", False):
			update_child_qty_rate("Quotation", items, quotation.name)
		quotation.reload()
		self.assertEqual(quotation.quote_revision_count, 1)
		versions = frappe.get_all(
			"Version", filters={"ref_doctype": "Quotation", "docname": quotation.name}, pluck="data"
		)
		self.assertTrue(any(json.loads(data).get("row_changed") for data in versions))
		update_child_qty_rate("Quotation", self.update_items_payload(quotation), quotation.name)
		quotation.reload()
		self.assertEqual(quotation.quote_revision_count, 1)

	def test_submitted_item_addition_and_removal_are_counted(self):
		quotation = make_quotation()
		items = self.update_items_payload(quotation)
		items.append({"item_code": "_Test Item 2", "qty": 2, "rate": 50})
		update_child_qty_rate("Quotation", items, quotation.name)
		quotation.reload()
		self.assertEqual(quotation.quote_revision_count, 1)
		update_child_qty_rate("Quotation", self.update_items_payload(quotation)[:1], quotation.name)
		quotation.reload()
		self.assertEqual(quotation.quote_revision_count, 2)

	def test_revision_submission_and_cancellation_track_current_version(self):
		source = make_quotation()
		first = source.make_revision().insert()
		self.assertTrue(source.reload().is_latest_revision)
		self.assertFalse(first.is_latest_revision)
		self.assertTrue(make_sales_order(source.name).items)
		first.submit()
		second = first.make_revision().insert()
		self.assertEqual(second.name, f"{source.name}-REV-2")
		self.assertEqual(second.original_quotation, source.name)
		self.assertEqual(second.revised_from, first.name)
		self.assertCountEqual(second.get_revisions(), [source.name, first.name, second.name])
		second.submit()
		for quotation in (source, first):
			quotation.reload()
			self.assertEqual(quotation.status, "Superseded")
			self.assertFalse(quotation.is_latest_revision)
			self.assertRaises(frappe.ValidationError, quotation.make_revision)
		self.assertTrue(second.is_latest_revision)
		self.assertEqual(second.status, "Open")
		order = make_sales_order(second.name)
		self.assertEqual(order.items[0].quotation_item, second.items[0].name)
		reason = frappe.get_doc(
			{
				"doctype": "Quotation Lost Reason",
				"order_lost_reason": f"_Test Revision Cancellation {frappe.generate_hash(length=8)}",
			}
		).insert()
		second.declare_enquiry_lost([{"lost_reason": reason.name}], [])
		self.assertTrue(second.reload().lost_reasons)
		second.cancel().reload()
		self.assertFalse(second.lost_reasons)
		self.assertFalse(second.is_latest_revision)
		self.assertEqual(second.status, "Cancelled")
		self.assertTrue(first.reload().is_latest_revision)
		self.assertEqual(first.status, "Open")

	def test_cannot_cancel_source_with_a_draft_revision(self):
		source = make_quotation()
		revision = source.make_revision().insert()
		with self.assertRaisesRegex(frappe.ValidationError, "Delete draft revision"):
			source.reload().cancel()
		revision.delete()
		source.reload().cancel()
		self.assertEqual(source.status, "Cancelled")
		self.assertRaises(frappe.ValidationError, source.make_revision)

	def test_cannot_submit_older_sibling_after_newer_version(self):
		source = make_quotation()
		first = source.make_revision().insert()
		second = source.make_revision().insert().submit()
		with self.assertRaisesRegex(frappe.ValidationError, "already the current version"):
			first.submit()
		self.assertTrue(second.reload().is_latest_revision)
		self.assertEqual(first.reload().docstatus, 0)

	def test_sibling_draft_cannot_replace_a_lost_current_revision(self):
		source = make_quotation()
		first = source.make_revision().insert()
		second = source.make_revision().insert()
		first.submit().declare_enquiry_lost([], [])
		self.assertRaises(frappe.ValidationError, first.make_revision)
		with self.assertRaisesRegex(frappe.ValidationError, "current quotation is Lost"):
			second.submit()
		self.assertTrue(first.reload().is_latest_revision)
		self.assertEqual(first.status, "Lost")

	def test_expired_revisions_renew_payment_dates(self):
		source = make_quotation(transaction_date=add_days(nowdate(), -20), do_not_submit=True)
		source.valid_till = add_days(nowdate(), -10)
		schedule = source.payment_schedule[0]
		schedule.due_date = add_days(nowdate(), -5)
		schedule.discount_type = "Percentage"
		schedule.discount = 2
		schedule.discount_date = add_days(nowdate(), -10)
		source.save().submit()
		self.assertEqual(source.status, "Expired")
		revision = source.make_revision().insert().submit()
		self.assertEqual(revision.status, "Open")
		self.assertEqual(getdate(revision.valid_till), getdate(add_days(nowdate(), 10)))
		self.assertEqual(getdate(revision.payment_schedule[0].due_date), getdate(add_days(nowdate(), 15)))
		self.assertEqual(
			getdate(revision.payment_schedule[0].discount_date), getdate(add_days(nowdate(), 10))
		)
		set_expired_status()
		self.assertEqual(source.reload().status, "Superseded")

	def test_superseded_versions_reject_mapping_and_item_updates(self):
		source = make_quotation()
		source.make_revision().insert().submit()
		self.assertRaises(frappe.ValidationError, make_sales_order, source.name)
		self.assertRaises(frappe.ValidationError, make_sales_invoice, source.name)
		items = self.update_items_payload(source)
		items[0]["qty"] += 1
		self.assertRaises(frappe.ValidationError, update_child_qty_rate, "Quotation", items, source.name)
		with self.assertRaisesRegex(frappe.ValidationError, "Only the current quotation"):
			source.declare_enquiry_lost([], [])
		self.assertEqual(source.reload().status, "Superseded")

	def test_revision_preserves_opportunity_item_references(self):
		opportunity = make_opportunity(with_items=1)
		source = make_opportunity_quotation(opportunity.name).insert().submit()
		revision = source.make_revision().insert().submit()
		self.assertEqual(revision.items[0].prevdoc_doctype, "Opportunity")
		self.assertEqual(revision.items[0].prevdoc_docname, opportunity.name)
		self.assertTrue(opportunity.reload().has_active_quotation())
		with self.assertRaisesRegex(frappe.ValidationError, "active Quotation exists"):
			opportunity.declare_enquiry_lost([], [])
		self.make_order(revision, 1).submit()
		self.assertTrue(opportunity.reload().has_ordered_quotation())

	def test_saved_transactions_reject_superseded_quotations(self):
		for doctype in ("Sales Order", "Sales Invoice"):
			with self.subTest(doctype=doctype):
				source = make_quotation()
				transaction = self.make_quotation_transaction(source, doctype)
				fieldname = "quotation" if doctype == "Sales Invoice" else "prevdoc_docname"
				self.assertEqual(transaction.reload().items[0].get(fieldname), source.name)
				source.make_revision().insert().submit()
				with self.assertRaisesRegex(frappe.ValidationError, "superseded"):
					transaction.save()
				with self.assertRaisesRegex(frappe.ValidationError, "superseded"):
					transaction.reload().submit()
				self.assertEqual(transaction.reload().docstatus, 0)

	def test_submitted_transactions_block_revision_until_cancelled(self):
		for doctype in ("Sales Order", "Sales Invoice"):
			with self.subTest(doctype=doctype):
				source = make_quotation()
				revision = source.make_revision().insert()
				transaction = self.make_quotation_transaction(source, doctype).submit()
				self.assertRaises(frappe.ValidationError, source.reload().make_revision)
				with self.assertRaisesRegex(frappe.ValidationError, f"submitted {doctype}"):
					revision.submit()
				transaction.cancel()
				revision.reload().submit()
				self.assertTrue(revision.is_latest_revision)

	def test_credit_note_accepts_historical_quotation(self):
		source = make_quotation()
		invoice = make_sales_invoice(source.name).insert().submit()
		# Historical invoices must remain returnable after their offer is superseded.
		source.db_set("is_latest_revision", 0)
		source.db_set("status", "Superseded")
		credit_note = make_sales_return(invoice.name)
		self.assertEqual(credit_note.items[0].quotation, source.name)
		credit_note.insert().submit()
		self.assertEqual(credit_note.docstatus, 1)

	def test_existing_quotation_can_be_revised(self):
		# Existing quotations did not run the new revision initialization hook.
		with patch.object(Quotation, "before_insert"):
			source = make_quotation()
		revision = source.make_revision().insert()
		invoice = make_sales_invoice(source.name).insert().submit()
		with self.assertRaisesRegex(frappe.ValidationError, "submitted Sales Invoice"):
			source.make_revision()
		with self.assertRaisesRegex(frappe.ValidationError, "submitted Sales Invoice"):
			revision.submit()

		invoice.cancel()
		revision.reload().submit()
		self.assertEqual(revision.original_quotation, source.name)
		self.assertEqual(revision.quotation_version, 1)
		self.assertTrue(revision.is_latest_revision)
		self.assertEqual(source.reload().status, "Superseded")

	def test_amended_revision_can_become_current(self):
		source = make_quotation()
		revision = source.make_revision().insert().submit()
		revision.cancel()
		amendment = frappe.copy_doc(revision, ignore_no_copy=False)
		amendment.docstatus = 0
		amendment.amended_from = revision.name
		amendment.insert().submit()
		self.assertTrue(amendment.is_latest_revision)
		self.assertEqual(amendment.original_quotation, source.name)
		self.assertEqual(amendment.quotation_version, 1)
		self.assertEqual(source.reload().status, "Superseded")
		self.assertEqual(amendment.make_revision().insert().quotation_version, 2)

	def test_revision_name_length_limits(self):
		valid_source = make_quotation(do_not_save=True)
		valid_source.insert(set_name="Q" * 120).submit()
		revision = valid_source.make_revision().insert()
		self.assertEqual(revision.name, f"{valid_source.name}-REV-1")
		source = make_quotation(do_not_save=True)
		source.insert(set_name="Q" * 135).submit()
		with self.assertRaisesRegex(frappe.ValidationError, "too long"):
			source.make_revision().insert()
		self.assertFalse(frappe.db.exists("Quotation", {"original_quotation": source.name}))

	def test_read_only_sharing_does_not_grant_create_permission(self):
		source = make_quotation()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "quotation-readonly@example.test",
				"first_name": "Quotation Test",
				"send_welcome_email": 0,
			}
		).insert()
		add("Quotation", source.name, user=user.name, read=1, notify=0)
		with self.set_user(user.name):
			self.assertTrue(frappe.has_permission("Quotation", "read", doc=source))
			self.assertRaises(frappe.PermissionError, source.make_revision)

	def test_concurrent_creation_allocates_distinct_numbers(self):
		self.setup_revision_requests()
		gate = Barrier(2)
		futures = [self.pool.submit(self.request, self.create_revision, gate) for _ in range(2)]
		names = [future.result(timeout=30) for future in futures]
		self.assertCountEqual(names, [f"{self.source}-REV-1", f"{self.source}-REV-2"])

	def test_order_and_revision_submission_cannot_both_succeed(self):
		self.setup_revision_requests()
		self.check_transaction_submission("Sales Order")

	def test_invoice_and_revision_submission_cannot_both_succeed(self):
		self.setup_revision_requests()
		self.check_transaction_submission("Sales Invoice")

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_funnel_counts_family_once_through_revision_and_cancellation(self):
		before = self.funnel_count()
		source = self.make_opportunity_quotation()
		revision = source.make_revision().insert()
		self.assertEqual(self.funnel_count() - before, 1)
		revision.submit()
		self.assertEqual(self.funnel_count() - before, 1)
		revision.cancel()
		self.assertEqual(self.funnel_count() - before, 1)

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_campaign_counts_current_quotation_including_original_draft(self):
		lead = frappe.get_doc({"doctype": "Lead", "first_name": "_Test Revision Campaign"}).insert()
		source = make_quotation(do_not_save=True, transaction_date="2026-06-01")
		source.quotation_to = "Lead"
		source.party_name = lead.name
		source.insert()
		self.assertEqual(get_lead_quotation_count([lead.name]), 1)
		source.submit()
		revision = source.make_revision().insert()
		self.assertEqual(get_lead_quotation_count([lead.name]), 1)
		revision.submit()
		self.assertEqual(get_lead_quotation_count([lead.name]), 1)
		revision.cancel()
		self.assertEqual(get_lead_quotation_count([lead.name]), 1)

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_trends_count_current_version_and_restore_after_cancellation(self):
		before = self.trends_amount()
		source = make_quotation(qty=2, rate=100, transaction_date="2026-06-01")
		revision = self.make_revision(source)
		self.assertEqual(self.trends_amount() - before, revision.base_net_total)
		revision.cancel()
		self.assertEqual(self.trends_amount() - before, source.base_net_total)

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_analytics_count_current_version_in_each_dimension(self):
		source = make_quotation(qty=2, rate=100, transaction_date="2026-06-01")
		dimensions = (
			("Customer", source.party_name),
			("Item", source.items[0].item_code),
			("Customer Group", source.customer_group),
			("Territory", source.territory),
			("Item Group", source.items[0].item_group),
			("Order Type", source.order_type),
		)
		before = {dimension: self.analytics_amount(*dimension) for dimension in dimensions}
		revision = self.make_revision(source)
		for dimension in dimensions:
			with self.subTest(dimension=dimension):
				self.assertEqual(
					self.analytics_amount(*dimension) - before[dimension],
					revision.base_net_total - source.base_net_total,
				)

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_reports_preserve_versions_in_closed_periods(self):
		before_funnel = self.funnel_count()
		source = self.make_opportunity_quotation()
		first = self.make_revision(source)
		dimensions = (
			("Customer", source.party_name),
			("Item", source.items[0].item_code),
			("Customer Group", source.customer_group),
			("Territory", source.territory),
			("Item Group", source.items[0].item_group),
			("Order Type", source.order_type),
		)
		before_analytics = {dimension: self.analytics_amount(*dimension) for dimension in dimensions}
		before_months = self.analytics_amount("Customer", source.party_name, to_date="2026-07-31")
		before_june = self.trends_amount(period="Monthly", column="Jun (Amt)")
		before_july = self.trends_amount(period="Monthly", column="Jul (Amt)")
		with freeze_time("2026-07-01 09:00:00.123456"):
			later = self.make_revision(first)
		self.assertEqual(self.funnel_count() - before_funnel, 1)
		self.assertEqual(self.trends_amount(period="Monthly", column="Jun (Amt)"), before_june)
		self.assertEqual(
			self.trends_amount(period="Monthly", column="Jul (Amt)") - before_july, later.base_net_total
		)
		for dimension in dimensions:
			with self.subTest(dimension=dimension):
				self.assertEqual(self.analytics_amount(*dimension), before_analytics[dimension])
		self.assertEqual(
			self.analytics_amount("Customer", source.party_name, to_date="2026-07-31") - before_months,
			later.base_net_total,
		)
		before_year = self.trends_amount()
		with freeze_time("2027-01-01 09:00:00.123456"):
			self.make_revision(later)
		self.assertEqual(self.trends_amount(), before_year)

	@freeze_time("2026-06-01 09:00:00.123456")
	def test_territory_counts_current_offers_and_preserves_historical_orders(self):
		before_orders = self.territory_amount("order_amount")
		before_quotations = self.territory_amount("quotation_amount")
		source = self.make_opportunity_quotation()
		revision = self.make_revision(source)
		self.assertEqual(
			self.territory_amount("quotation_amount") - before_quotations, revision.base_grand_total
		)
		order = make_sales_order(revision.name)
		order.transaction_date = revision.transaction_date
		order.delivery_date = "2026-06-02"
		order.insert().submit()
		# Earlier versions allowed orders against several revisions of the same quotation.
		revision.db_set("is_latest_revision", 0)
		self.assertEqual(self.territory_amount("quotation_amount"), before_quotations)
		self.assertEqual(self.territory_amount("order_amount") - before_orders, order.base_grand_total)

	@staticmethod
	def update_items_payload(quotation):
		return [
			{
				"docname": row.name,
				"item_code": row.item_code,
				"qty": row.qty,
				"rate": row.rate,
				"description": row.description,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
			}
			for row in quotation.items
		]

	@staticmethod
	def make_order(source, quantity):
		order = make_sales_order(source.name)
		order.delivery_date = add_days(nowdate(), 5)
		for item in order.items:
			item.delivery_date = order.delivery_date
			item.qty = quantity
		return order.insert()

	def setup_revision_requests(self):
		self.site = frappe.local.site
		self.sites_path = frappe.local.sites_path
		self.pool = ThreadPoolExecutor(max_workers=2)
		self.addCleanup(self.pool.shutdown)
		self.source = self.pool.submit(self.request, self.create_source).result(timeout=30)
		self.addCleanup(self.cleanup_source)

	def check_transaction_submission(self, doctype):
		revision = self.pool.submit(self.request, self.create_revision).result(timeout=30)
		create_transaction = self.create_order if doctype == "Sales Order" else self.create_invoice
		transaction = self.pool.submit(self.request, create_transaction).result(timeout=30)
		gate = Barrier(2)
		futures = [
			self.pool.submit(self.request, self.submit_document, doctype, name, gate)
			for doctype, name in (("Quotation", revision), (doctype, transaction))
		]
		results = [future.result(timeout=30) for future in futures]
		self.assertCountEqual(results, ["submitted", "rejected"])

	def request(self, action, *args):
		frappe.init(site=self.site, sites_path=self.sites_path)
		frappe.connect()
		frappe.set_user("Administrator")
		frappe.flags.mute_emails = True
		try:
			result = action(*args)
			# Separate committed requests are required to exercise actual database locks.
			frappe.db.commit()  # nosemgrep: frappe-manual-commit, Dont-commit
			return result
		except Exception:
			frappe.db.rollback()
			raise
		finally:
			frappe.destroy()

	def create_source(self):
		source = make_quotation(do_not_save=True)
		source.insert(set_name=f"_Test Quotation {self._testMethodName}").submit()
		return source.name

	def create_revision(self, gate=None):
		if gate:
			gate.wait(timeout=15)
		return frappe.get_doc("Quotation", self.source).make_revision().insert().name

	def create_order(self):
		return self.make_order(frappe.get_doc("Quotation", self.source), 10).name

	def create_invoice(self):
		return make_sales_invoice(self.source).insert().name

	@staticmethod
	def submit_document(doctype, name, gate):
		doc = frappe.get_doc(doctype, name)
		gate.wait(timeout=15)
		try:
			doc.submit()
			return "submitted"
		except frappe.ValidationError:
			frappe.db.rollback()
			return "rejected"

	def cleanup_source(self):
		frappe.db.rollback()
		self.pool.submit(self.request, self.delete_source).result(timeout=30)

	def delete_source(self):
		for doctype, fieldname in (("Sales Invoice", "quotation"), ("Sales Order", "prevdoc_docname")):
			for name in frappe.get_all(f"{doctype} Item", filters={fieldname: self.source}, pluck="parent"):
				transaction = frappe.get_doc(doctype, name)
				if transaction.docstatus == 1:
					transaction.cancel()
				transaction.delete()
		for name in frappe.get_all(
			"Quotation",
			filters={"original_quotation": self.source},
			pluck="name",
			order_by="quotation_version desc",
		):
			revision = frappe.get_doc("Quotation", name)
			if revision.docstatus == 1:
				revision.cancel()
			revision.delete()
		source = frappe.get_doc("Quotation", self.source)
		source.cancel()
		source.delete()
		frappe.db.delete("Series", {"name": f"{self.source}-REV-"})

	@staticmethod
	def make_revision(source):
		revision = source.make_revision()
		revision.items[0].qty = 3
		revision.items[0].rate = 150
		return revision.insert().submit()

	@staticmethod
	def funnel_count():
		return next(
			row["value"]
			for row in get_funnel_data("2026-06-01", "2026-06-30", "_Test Company")
			if row["title"] == "Quotations"
		)

	@staticmethod
	def trends_amount(period="Yearly", column="Total(Amt)"):
		columns, rows, *_ = quotation_trends(
			frappe._dict(
				company="_Test Company",
				fiscal_year="_Test Fiscal Year 2026",
				based_on="Item",
				period=period,
			)
		)
		labels = [column.split(":")[0] if isinstance(column, str) else column["label"] for column in columns]
		return next((row[labels.index(column)] or 0 for row in rows if row[0] == "_Test Item"), 0)

	@staticmethod
	def analytics_amount(tree_type, entity, to_date="2026-06-30"):
		_, rows, *_ = sales_analytics(
			{
				"doc_type": "Quotation",
				"tree_type": tree_type,
				"entity": [entity],
				"value_quantity": "Value",
				"range": "Monthly",
				"company": "_Test Company",
				"from_date": "2026-06-01",
				"to_date": to_date,
				"curves": "all",
			}
		)
		return next((row["total"] for row in rows if row["entity"] == entity), 0)

	@staticmethod
	def territory_amount(field):
		_, rows = territory_sales(frappe._dict(company="_Test Company"))
		return next(row[field] for row in rows if row["territory"] == "_Test Territory")

	@staticmethod
	def make_opportunity_quotation():
		opportunity = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": "_Test Customer",
				"territory": "_Test Territory",
				"company": "_Test Company",
				"currency": "INR",
				"opportunity_amount": 5000,
				"transaction_date": "2026-06-01",
			}
		).insert()
		source = make_quotation(qty=2, rate=100, transaction_date="2026-06-01", do_not_save=True)
		source.opportunity = opportunity.name
		return source.insert().submit()

	def make_quotation_transaction(self, source, doctype):
		if doctype == "Sales Order":
			return self.make_order(source, 4)
		return make_sales_invoice(source.name).insert()


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


def make_terms_and_conditions(copy_attachments_to_transaction=False):
	return frappe.get_doc(
		{
			"doctype": "Terms and Conditions",
			"title": f"_Test Terms and Conditions {frappe.generate_hash(length=8)}",
			"selling": 1,
			"terms": "Test terms",
			"copy_attachments_to_transaction": 1 if copy_attachments_to_transaction else 0,
		}
	).insert()


def make_file_attachment(doctype, docname, content):
	return frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"terms-attachment-{frappe.generate_hash(length=8)}.txt",
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"content": content,
		}
	).insert()


def get_attachment_urls(doctype, docname):
	return {
		file.file_url
		for file in frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": docname},
			fields=["file_url"],
		)
		if file.file_url
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
				"qty": args.qty if args.qty is not None else 10,
				"uom": args.uom or None,
				"rate": args.rate or 100,
			},
		)

	if not args.do_not_save:
		qo.insert()
		if not args.do_not_submit:
			qo.submit()

	return qo
