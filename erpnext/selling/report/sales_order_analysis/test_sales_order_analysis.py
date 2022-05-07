import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.report.sales_order_analysis.sales_order_analysis import execute
from erpnext.stock.doctype.item.test_item import create_item

test_dependencies = ["Sales Order", "Item", "Sales Invoice", "Delivery Note"]


class TestSalesOrderAnalysis(FrappeTestCase):
	def create_sales_order(self, transaction_date):
		item = create_item(item_code="_Test Excavator", is_stock_item=0)
		so = make_sales_order(
			transaction_date=transaction_date,
			item=item.item_code,
			qty=10,
			rate=100000,
			do_not_save=True,
		)
		so.po_no = ""
		so.taxes_and_charges = ""
		so.taxes = ""
		so.items[0].delivery_date = add_days(transaction_date, 15)
		so.save()
		so.submit()
		return item, so

	def create_sales_invoice(self, so):
		sinv = make_sales_invoice(so.name)
		sinv.posting_date = so.transaction_date
		sinv.taxes_and_charges = ""
		sinv.taxes = ""
		sinv.insert()
		sinv.submit()
		return sinv

	def create_delivery_note(self, so):
		dn = make_delivery_note(so.name)
		dn.set_posting_time = True
		dn.posting_date = add_days(so.transaction_date, 1)
		dn.save()
		dn.submit()
		return dn

	def test_01_so_to_deliver_and_bill(self):
		transaction_date = "2021-06-01"
		item, so = self.create_sales_order(transaction_date)
		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"from_date": "2021-06-01",
				"to_date": "2021-06-30",
				"status": ["To Deliver and Bill"],
			}
		)
		expected_value = {
			"status": "To Deliver and Bill",
			"sales_order": so.name,
			"delay_days": frappe.utils.date_diff(frappe.utils.datetime.date.today(), so.delivery_date),
			"qty": 10,
			"delivered_qty": 0,
			"pending_qty": 10,
			"qty_to_bill": 10,
			"time_taken_to_deliver": 0,
		}
		self.assertEqual(len(data), 1)
		for key, val in expected_value.items():
			with self.subTest(key=key, val=val):
				self.assertEqual(data[0][key], val)

	def test_02_so_to_deliver(self):
		transaction_date = "2021-06-01"
		item, so = self.create_sales_order(transaction_date)
		self.create_sales_invoice(so)
		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"from_date": "2021-06-01",
				"to_date": "2021-06-30",
				"status": ["To Deliver"],
			}
		)
		expected_value = {
			"status": "To Deliver",
			"sales_order": so.name,
			"delay_days": frappe.utils.date_diff(frappe.utils.datetime.date.today(), so.delivery_date),
			"qty": 10,
			"delivered_qty": 0,
			"pending_qty": 10,
			"qty_to_bill": 0,
			"time_taken_to_deliver": 0,
		}
		self.assertEqual(len(data), 1)
		for key, val in expected_value.items():
			with self.subTest(key=key, val=val):
				self.assertEqual(data[0][key], val)

	def test_03_so_to_bill(self):
		transaction_date = "2021-06-01"
		item, so = self.create_sales_order(transaction_date)
		self.create_delivery_note(so)
		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"from_date": "2021-06-01",
				"to_date": "2021-06-30",
				"status": ["To Bill"],
			}
		)
		expected_value = {
			"status": "To Bill",
			"sales_order": so.name,
			"delay_days": frappe.utils.date_diff(frappe.utils.datetime.date.today(), so.delivery_date),
			"qty": 10,
			"delivered_qty": 10,
			"pending_qty": 0,
			"qty_to_bill": 10,
			"time_taken_to_deliver": 86400,
		}
		self.assertEqual(len(data), 1)
		for key, val in expected_value.items():
			with self.subTest(key=key, val=val):
				self.assertEqual(data[0][key], val)

	def test_04_so_completed(self):
		transaction_date = "2021-06-01"
		item, so = self.create_sales_order(transaction_date)
		self.create_sales_invoice(so)
		self.create_delivery_note(so)
		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"from_date": "2021-06-01",
				"to_date": "2021-06-30",
				"status": ["Completed"],
			}
		)
		expected_value = {
			"status": "Completed",
			"sales_order": so.name,
			"delay_days": frappe.utils.date_diff(frappe.utils.datetime.date.today(), so.delivery_date),
			"qty": 10,
			"delivered_qty": 10,
			"pending_qty": 0,
			"qty_to_bill": 0,
			"billed_qty": 10,
			"time_taken_to_deliver": 86400,
		}
		self.assertEqual(len(data), 1)
		for key, val in expected_value.items():
			with self.subTest(key=key, val=val):
				self.assertEqual(data[0][key], val)

	def test_05_all_so_status(self):
		columns, data, message, chart = execute(
			{
				"company": "_Test Company",
				"from_date": "2021-06-01",
				"to_date": "2021-06-30",
			}
		)
		# SO's from first 4 test cases should be in output
		self.assertEqual(len(data), 4)
