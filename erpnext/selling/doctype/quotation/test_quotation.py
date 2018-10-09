# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe.utils import flt, add_days, nowdate, add_months
import unittest

test_dependencies = ["Product Bundle"]


class TestQuotation(unittest.TestCase):
	def test_make_quotation_without_terms(self):
		quotation = make_quotation(do_not_save=1)
		self.assertFalse(quotation.get('payment_schedule'))

		quotation.insert()

		self.assertTrue(quotation.payment_schedule)

	def test_make_sales_order_terms_not_copied(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()
		quotation.submit()

		sales_order = make_sales_order(quotation.name)

		self.assertFalse(sales_order.get('payment_schedule'))

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

		sales_order.delivery_date = "2014-01-01"
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.insert()

	def test_make_sales_order_with_terms(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.update(
			{"payment_terms_template": "_Test Payment Term Template"}
		)
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

		sales_order.delivery_date = "2014-01-01"
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.insert()

		self.assertEqual(sales_order.payment_schedule[0].payment_amount, 8906.00)
		self.assertEqual(sales_order.payment_schedule[0].due_date, quotation.transaction_date)
		self.assertEqual(sales_order.payment_schedule[1].payment_amount, 8906.00)
		self.assertEqual(
			sales_order.payment_schedule[1].due_date, add_days(quotation.transaction_date, 30)
		)

	def test_valid_till(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order

		quotation = frappe.copy_doc(test_records[0])
		quotation.valid_till = add_days(quotation.transaction_date, -1)
		self.assertRaises(frappe.ValidationError, quotation.validate)

		quotation.valid_till = add_days(nowdate(), -1)
		quotation.insert()
		quotation.submit()
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)

	def test_create_quotation_with_margin(self):
		from erpnext.selling.doctype.quotation.quotation import make_sales_order
		from erpnext.selling.doctype.sales_order.sales_order \
			import make_delivery_note, make_sales_invoice

		rate_with_margin = flt((1500*18.75)/100 + 1500)

		test_records[0]['items'][0]['price_list_rate'] = 1500
		test_records[0]['items'][0]['margin_type'] = 'Percentage'
		test_records[0]['items'][0]['margin_rate_or_amount'] = 18.75

		quotation = frappe.copy_doc(test_records[0])
		quotation.transaction_date = nowdate()
		quotation.valid_till = add_months(quotation.transaction_date, 1)
		quotation.insert()

		self.assertEqual(quotation.get("items")[0].rate, rate_with_margin)
		self.assertRaises(frappe.ValidationError, make_sales_order, quotation.name)
		quotation.submit()

		sales_order = make_sales_order(quotation.name)
		sales_order.naming_series = "_T-Quotation-"
		sales_order.transaction_date = nowdate()
		sales_order.delivery_date = add_months(nowdate(), 1)

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

		first_item = make_item("_Test Laptop",
							{"is_stock_item": 1})

		second_item = make_item("_Test CPU",
							{"is_stock_item": 1})

		qo_item1 = [
			{
				"item_code": first_item.item_code,
				"warehouse": "",
				"qty": 2,
				"rate": 400,
				"delivered_by_supplier": 1,
				"supplier": '_Test Supplier'
			}
		]

		qo_item2 = [
			{
				"item_code": second_item.item_code,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 2,
				"rate": 300,
				"conversion_factor": 1.0
			}
		]

		first_qo = make_quotation(item_list=qo_item1, do_not_submit=True)
		first_qo.submit()
		sec_qo = make_quotation(item_list=qo_item2, do_not_submit=True)
		sec_qo.submit()

test_records = frappe.get_test_records('Quotation')

def get_quotation_dict(customer=None, item_code=None):
	if not customer:
		customer = '_Test Customer'
	if not item_code:
		item_code = '_Test Item'

	return {
		'doctype': 'Quotation',
		'customer': customer,
		'items': [
			{
				'item_code': item_code,
				'qty': 1,
				'rate': 100
			}
		]
	}


def make_quotation(**args):
	qo = frappe.new_doc("Quotation")
	args = frappe._dict(args)
	if args.transaction_date:
		qo.transaction_date = args.transaction_date

	qo.company = args.company or "_Test Company"
	qo.customer = args.customer or "_Test Customer"
	qo.currency = args.currency or "INR"
	if args.selling_price_list:
		qo.selling_price_list = args.selling_price_list

	if "warehouse" not in args:
		args.warehouse = "_Test Warehouse - _TC"

	if args.item_list:
		for item in args.item_list:
			qo.append("items", item)

	else:
		qo.append("items", {
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse,
			"qty": args.qty or 10,
			"uom": args.uom or None,
			"rate": args.rate or 100
		})

	qo.delivery_date = add_days(qo.transaction_date, 10)

	if not args.do_not_save:
		qo.insert()
		if not args.do_not_submit:
			qo.submit()

	return qo
