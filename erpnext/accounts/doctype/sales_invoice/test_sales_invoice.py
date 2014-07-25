# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import unittest, json, copy
from frappe.utils import flt
from erpnext.accounts.utils import get_stock_and_account_difference
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
from erpnext.projects.doctype.time_log_batch.test_time_log_batch import *


class TestSalesInvoice(unittest.TestCase):
	def make(self):
		w = frappe.copy_doc(test_records[0])
		w.is_pos = 0
		w.insert()
		w.submit()
		return w

	def test_timestamp_change(self):
		w = frappe.copy_doc(test_records[0])
		w.docstatus = 0
		w.insert()

		w2 = frappe.get_doc(w.doctype, w.name)

		import time
		time.sleep(1)
		w.save()

		import time
		time.sleep(1)
		self.assertRaises(frappe.TimestampMismatchError, w2.save)

	def test_sales_invoice_calculation_base_currency(self):
		si = frappe.copy_doc(test_records[2])
		si.insert()

		expected_values = {
			"keys": ["price_list_rate", "discount_percentage", "rate", "amount",
				"base_price_list_rate", "base_rate", "base_amount"],
			"_Test Item Home Desktop 100": [50, 0, 50, 500, 50, 50, 500],
			"_Test Item Home Desktop 200": [150, 0, 150, 750, 150, 150, 750],
		}

		# check if children are saved
		self.assertEquals(len(si.get("entries")),
			len(expected_values)-1)

		# check if item values are calculated
		for d in si.get("entries"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEquals(si.net_total, 1250)
		self.assertEquals(si.net_total_export, 1250)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Shipping Charges - _TC": [100, 1350],
			"_Test Account Customs Duty - _TC": [125, 1475],
			"_Test Account Excise Duty - _TC": [140, 1615],
			"_Test Account Education Cess - _TC": [2.8, 1617.8],
			"_Test Account S&H Education Cess - _TC": [1.4, 1619.2],
			"_Test Account CST - _TC": [32.38, 1651.58],
			"_Test Account VAT - _TC": [156.25, 1807.83],
			"_Test Account Discount - _TC": [-180.78, 1627.05]
		}

		for d in si.get("other_charges"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.account_head][i])

		self.assertEquals(si.grand_total, 1627.05)
		self.assertEquals(si.grand_total_export, 1627.05)

	def test_sales_invoice_calculation_export_currency(self):
		si = frappe.copy_doc(test_records[2])
		si.currency = "USD"
		si.conversion_rate = 50
		si.get("entries")[0].rate = 1
		si.get("entries")[0].price_list_rate = 1
		si.get("entries")[1].rate = 3
		si.get("entries")[1].price_list_rate = 3
		si.insert()

		expected_values = {
			"keys": ["price_list_rate", "discount_percentage", "rate", "amount",
				"base_price_list_rate", "base_rate", "base_amount"],
			"_Test Item Home Desktop 100": [1, 0, 1, 10, 50, 50, 500],
			"_Test Item Home Desktop 200": [3, 0, 3, 15, 150, 150, 750],
		}

		# check if children are saved
		self.assertEquals(len(si.get("entries")),
			len(expected_values)-1)

		# check if item values are calculated
		for d in si.get("entries"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEquals(si.net_total, 1250)
		self.assertEquals(si.net_total_export, 25)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Shipping Charges - _TC": [100, 1350],
			"_Test Account Customs Duty - _TC": [125, 1475],
			"_Test Account Excise Duty - _TC": [140, 1615],
			"_Test Account Education Cess - _TC": [2.8, 1617.8],
			"_Test Account S&H Education Cess - _TC": [1.4, 1619.2],
			"_Test Account CST - _TC": [32.38, 1651.58],
			"_Test Account VAT - _TC": [156.25, 1807.83],
			"_Test Account Discount - _TC": [-180.78, 1627.05]
		}

		for d in si.get("other_charges"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.account_head][i])

		self.assertEquals(si.grand_total, 1627.05)
		self.assertEquals(si.grand_total_export, 32.54)

	def test_sales_invoice_discount_amount(self):
		si = frappe.copy_doc(test_records[3])
		si.discount_amount = 104.95
		si.append("other_charges", {
			"doctype": "Sales Taxes and Charges",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account Service Tax - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Service Tax",
			"rate": 10,
			"row_id": 8,
		})
		si.insert()

		expected_values = {
			"keys": ["price_list_rate", "discount_percentage", "rate", "amount",
				"base_price_list_rate", "base_rate", "base_amount"],
			"_Test Item Home Desktop 100": [62.5, 0, 62.5, 625.0, 50, 50, 465.37],
			"_Test Item Home Desktop 200": [190.66, 0, 190.66, 953.3, 150, 150, 698.08],
		}

		# check if children are saved
		self.assertEquals(len(si.get("entries")),
			len(expected_values)-1)

		# check if item values are calculated
		for d in si.get("entries"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEquals(si.net_total, 1163.45)
		self.assertEquals(si.net_total_export, 1578.3)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "tax_amount_after_discount_amount", "total"],
			"_Test Account Excise Duty - _TC": [140, 130.31, 1293.76],
			"_Test Account Education Cess - _TC": [2.8, 2.61, 1296.37],
			"_Test Account S&H Education Cess - _TC": [1.4, 1.31, 1297.68],
			"_Test Account CST - _TC": [27.88, 25.96, 1323.64],
			"_Test Account VAT - _TC": [156.25, 145.43, 1469.07],
			"_Test Account Customs Duty - _TC": [125, 116.35, 1585.42],
			"_Test Account Shipping Charges - _TC": [100, 100, 1685.42],
			"_Test Account Discount - _TC": [-180.33, -168.54, 1516.88],
			"_Test Account Service Tax - _TC": [-18.03, -16.88, 1500]
		}

		for d in si.get("other_charges"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.account_head][i])

		self.assertEquals(si.grand_total, 1500)
		self.assertEquals(si.grand_total_export, 1500)

	def test_discount_amount_gl_entry(self):
		si = frappe.copy_doc(test_records[3])
		si.discount_amount = 104.95
		si.append("other_charges", {
			"doctype": "Sales Taxes and Charges",
			"charge_type": "On Previous Row Amount",
			"account_head": "_Test Account Service Tax - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Service Tax",
			"rate": 10,
			"row_id": 8
		})
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = sorted([
			[si.debit_to, 1500, 0.0],
			[test_records[3]["entries"][0]["income_account"], 0.0, 1163.45],
			[test_records[3]["other_charges"][0]["account_head"], 0.0, 130.31],
			[test_records[3]["other_charges"][1]["account_head"], 0.0, 2.61],
			[test_records[3]["other_charges"][2]["account_head"], 0.0, 1.31],
			[test_records[3]["other_charges"][3]["account_head"], 0.0, 25.96],
			[test_records[3]["other_charges"][4]["account_head"], 0.0, 145.43],
			[test_records[3]["other_charges"][5]["account_head"], 0.0, 116.35],
			[test_records[3]["other_charges"][6]["account_head"], 0.0, 100],
			[test_records[3]["other_charges"][7]["account_head"], 168.54, 0.0],
			["_Test Account Service Tax - _TC", 16.88, 0.0],
		])

		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)

		# cancel
		si.cancel()

		gle = frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", si.name)

		self.assertFalse(gle)

	def test_inclusive_rate_validations(self):
		si = frappe.copy_doc(test_records[2])
		for i, tax in enumerate(si.get("other_charges")):
			tax.idx = i+1

		si.get("entries")[0].price_list_rate = 62.5
		si.get("entries")[0].price_list_rate = 191
		for i in xrange(6):
			si.get("other_charges")[i].included_in_print_rate = 1

		# tax type "Actual" cannot be inclusive
		self.assertRaises(frappe.ValidationError, si.insert)

		# taxes above included type 'On Previous Row Total' should also be included
		si.get("other_charges")[0].included_in_print_rate = 0
		self.assertRaises(frappe.ValidationError, si.insert)

	def test_sales_invoice_calculation_base_currency_with_tax_inclusive_price(self):
		# prepare
		si = frappe.copy_doc(test_records[3])
		si.insert()

		expected_values = {
			"keys": ["price_list_rate", "discount_percentage", "rate", "amount",
				"base_price_list_rate", "base_rate", "base_amount"],
			"_Test Item Home Desktop 100": [62.5, 0, 62.5, 625.0, 50, 50, 499.98],
			"_Test Item Home Desktop 200": [190.66, 0, 190.66, 953.3, 150, 150, 750],
		}

		# check if children are saved
		self.assertEquals(len(si.get("entries")),
			len(expected_values)-1)

		# check if item values are calculated
		for d in si.get("entries"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEquals(si.net_total, 1249.98)
		self.assertEquals(si.net_total_export, 1578.3)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Excise Duty - _TC": [140, 1389.98],
			"_Test Account Education Cess - _TC": [2.8, 1392.78],
			"_Test Account S&H Education Cess - _TC": [1.4, 1394.18],
			"_Test Account CST - _TC": [27.88, 1422.06],
			"_Test Account VAT - _TC": [156.25, 1578.31],
			"_Test Account Customs Duty - _TC": [125, 1703.31],
			"_Test Account Shipping Charges - _TC": [100, 1803.31],
			"_Test Account Discount - _TC": [-180.33, 1622.98]
		}

		for d in si.get("other_charges"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.account_head][i])

		self.assertEquals(si.grand_total, 1622.98)
		self.assertEquals(si.grand_total_export, 1622.98)

	def test_sales_invoice_calculation_export_currency_with_tax_inclusive_price(self):
		# prepare
		si = frappe.copy_doc(test_records[3])
		si.currency = "USD"
		si.conversion_rate = 50
		si.get("entries")[0].price_list_rate = 55.56
		si.get("entries")[0].discount_percentage = 10
		si.get("entries")[1].price_list_rate = 187.5
		si.get("entries")[1].discount_percentage = 20
		si.get("other_charges")[6].rate = 5000

		si.insert()

		expected_values = {
			"keys": ["price_list_rate", "discount_percentage", "rate", "amount",
				"base_price_list_rate", "base_rate", "base_amount"],
			"_Test Item Home Desktop 100": [55.56, 10, 50, 500, 2222.11, 1999.9, 19999.04],
			"_Test Item Home Desktop 200": [187.5, 20, 150, 750, 7375.66, 5900.53, 29502.66],
		}

		# check if children are saved
		self.assertEquals(len(si.get("entries")), len(expected_values)-1)

		# check if item values are calculated
		for d in si.get("entries"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.item_code][i])

		# check net total
		self.assertEquals(si.net_total, 49501.7)
		self.assertEquals(si.net_total_export, 1250)

		# check tax calculation
		expected_values = {
			"keys": ["tax_amount", "total"],
			"_Test Account Excise Duty - _TC": [5540.22, 55041.92],
			"_Test Account Education Cess - _TC": [110.81, 55152.73],
			"_Test Account S&H Education Cess - _TC": [55.4, 55208.13],
			"_Test Account CST - _TC": [1104.16, 56312.29],
			"_Test Account VAT - _TC": [6187.71, 62500],
			"_Test Account Customs Duty - _TC": [4950.17, 67450.17],
			"_Test Account Shipping Charges - _TC": [5000, 72450.17],
			"_Test Account Discount - _TC": [-7245.01, 65205.16]
		}

		for d in si.get("other_charges"):
			for i, k in enumerate(expected_values["keys"]):
				self.assertEquals(d.get(k), expected_values[d.account_head][i])

		self.assertEquals(si.grand_total, 65205.16)
		self.assertEquals(si.grand_total_export, 1304.1)

	def test_outstanding(self):
		w = self.make()
		self.assertEquals(w.outstanding_amount, w.grand_total)

	def test_payment(self):
		frappe.db.sql("""delete from `tabGL Entry`""")
		w = self.make()

		from erpnext.accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records

		jv = frappe.get_doc(frappe.copy_doc(jv_test_records[0]))
		jv.get("entries")[0].against_invoice = w.name
		jv.insert()
		jv.submit()

		self.assertEquals(frappe.db.get_value("Sales Invoice", w.name, "outstanding_amount"),
			161.8)

		jv.cancel()
		self.assertEquals(frappe.db.get_value("Sales Invoice", w.name, "outstanding_amount"),
			561.8)

	def test_time_log_batch(self):
		delete_time_log_and_batch()
		time_log = create_time_log()
		tlb = create_time_log_batch(time_log)

		tlb = frappe.get_doc("Time Log Batch", tlb.name)
		tlb.submit()

		si = frappe.get_doc(frappe.copy_doc(test_records[0]))
		si.get("entries")[0].time_log_batch = tlb.name
		si.insert()
		si.submit()

		self.assertEquals(frappe.db.get_value("Time Log Batch", tlb.name, "status"), "Billed")

		self.assertEquals(frappe.db.get_value("Time Log", time_log, "status"), "Billed")

		si.cancel()

		self.assertEquals(frappe.db.get_value("Time Log Batch", tlb.name, "status"), "Submitted")

		self.assertEquals(frappe.db.get_value("Time Log", time_log, "status"), "Batched for Billing")

		frappe.delete_doc("Sales Invoice", si.name)
		delete_time_log_and_batch()

	def test_sales_invoice_gl_entry_without_aii(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory(0)
		si = frappe.copy_doc(test_records[1])
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = sorted([
			[si.debit_to, 630.0, 0.0],
			[test_records[1]["entries"][0]["income_account"], 0.0, 500.0],
			[test_records[1]["other_charges"][0]["account_head"], 0.0, 80.0],
			[test_records[1]["other_charges"][1]["account_head"], 0.0, 50.0],
		])

		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)

		# cancel
		si.cancel()

		gle = frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", si.name)

		self.assertFalse(gle)

	def test_pos_gl_entry_with_aii(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		self.make_pos_setting()

		self._insert_purchase_receipt()

		pos = copy.deepcopy(test_records[1])
		pos["is_pos"] = 1
		pos["update_stock"] = 1
		pos["posting_time"] = "12:05"
		pos["cash_bank_account"] = "_Test Account Bank Account - _TC"
		pos["paid_amount"] = 600.0

		si = frappe.copy_doc(pos)
		si.insert()
		si.submit()

		# check stock ledger entries
		sle = frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type = 'Sales Invoice' and voucher_no = %s""",
			si.name, as_dict=1)[0]
		self.assertTrue(sle)
		self.assertEquals([sle.item_code, sle.warehouse, sle.actual_qty],
			["_Test Item", "_Test Warehouse - _TC", -1.0])

		# check gl entries
		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc, debit asc""", si.name, as_dict=1)
		self.assertTrue(gl_entries)

		stock_in_hand = frappe.db.get_value("Account", {"master_name": "_Test Warehouse - _TC"})

		expected_gl_entries = sorted([
			[si.debit_to, 630.0, 0.0],
			[pos["entries"][0]["income_account"], 0.0, 500.0],
			[pos["other_charges"][0]["account_head"], 0.0, 80.0],
			[pos["other_charges"][1]["account_head"], 0.0, 50.0],
			[stock_in_hand, 0.0, 75.0],
			[pos["entries"][0]["expense_account"], 75.0, 0.0],
			[si.debit_to, 0.0, 600.0],
			["_Test Account Bank Account - _TC", 600.0, 0.0]
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)

		si.cancel()
		gle = frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", si.name)

		self.assertFalse(gle)

		self.assertFalse(get_stock_and_account_difference([stock_in_hand]))

		set_perpetual_inventory(0)

		frappe.db.sql("delete from `tabPOS Setting`")

	def make_pos_setting(self):
		pos_setting = frappe.get_doc({
			"cash_bank_account": "_Test Account Bank Account - _TC",
			"company": "_Test Company",
			"cost_center": "_Test Cost Center - _TC",
			"currency": "INR",
			"doctype": "POS Setting",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"income_account": "Sales - _TC",
			"name": "_Test POS Setting",
			"naming_series": "_T-POS Setting-",
			"selling_price_list": "_Test Price List",
			"territory": "_Test Territory",
			"warehouse": "_Test Warehouse - _TC"
		})

		if not frappe.db.exists("POS Setting", "_Test POS Setting"):
			pos_setting.insert()

	def test_si_gl_entry_with_aii_and_update_stock_with_warehouse_but_no_account(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		frappe.delete_doc("Account", "_Test Warehouse No Account - _TC")

		# insert purchase receipt
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import test_records \
			as pr_test_records
		pr = frappe.copy_doc(pr_test_records[0])
		pr.naming_series = "_T-Purchase Receipt-"
		pr.get("purchase_receipt_details")[0].warehouse = "_Test Warehouse No Account - _TC"
		pr.insert()
		pr.submit()

		si_doc = copy.deepcopy(test_records[1])
		si_doc["update_stock"] = 1
		si_doc["posting_time"] = "12:05"
		si_doc.get("entries")[0]["warehouse"] = "_Test Warehouse No Account - _TC"

		si = frappe.copy_doc(si_doc)
		si.insert()
		si.submit()

		# check stock ledger entries
		sle = frappe.db.sql("""select * from `tabStock Ledger Entry`
			where voucher_type = 'Sales Invoice' and voucher_no = %s""",
			si.name, as_dict=1)[0]
		self.assertTrue(sle)
		self.assertEquals([sle.item_code, sle.warehouse, sle.actual_qty],
			["_Test Item", "_Test Warehouse No Account - _TC", -1.0])

		# check gl entries
		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc, debit asc""", si.name, as_dict=1)
		self.assertTrue(gl_entries)

		expected_gl_entries = sorted([
			[si.debit_to, 630.0, 0.0],
			[si_doc.get("entries")[0]["income_account"], 0.0, 500.0],
			[si_doc.get("other_charges")[0]["account_head"], 0.0, 80.0],
			[si_doc.get("other_charges")[1]["account_head"], 0.0, 50.0],
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)

		si.cancel()
		gle = frappe.db.sql("""select * from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", si.name)

		self.assertFalse(gle)
		set_perpetual_inventory(0)

	def test_sales_invoice_gl_entry_with_aii_no_item_code(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()

		si = frappe.get_doc(test_records[1])
		si.get("entries")[0].item_code = None
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.name, as_dict=1)
		self.assertTrue(gl_entries)

		expected_values = sorted([
			[si.debit_to, 630.0, 0.0],
			[test_records[1]["entries"][0]["income_account"], 0.0, 500.0],
			[test_records[1]["other_charges"][0]["account_head"], 0.0, 80.0],
			[test_records[1]["other_charges"][1]["account_head"], 0.0, 50.0],
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)

		set_perpetual_inventory(0)

	def test_sales_invoice_gl_entry_with_aii_non_stock_item(self):
		self.clear_stock_account_balance()
		set_perpetual_inventory()
		si = frappe.get_doc(test_records[1])
		si.get("entries")[0].item_code = "_Test Non Stock Item"
		si.insert()
		si.submit()

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.name, as_dict=1)
		self.assertTrue(gl_entries)

		expected_values = sorted([
			[si.debit_to, 630.0, 0.0],
			[test_records[1]["entries"][0]["income_account"], 0.0, 500.0],
			[test_records[1]["other_charges"][0]["account_head"], 0.0, 80.0],
			[test_records[1]["other_charges"][1]["account_head"], 0.0, 50.0],
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)

		set_perpetual_inventory(0)

	def _insert_purchase_receipt(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import test_records \
			as pr_test_records
		pr = frappe.copy_doc(pr_test_records[0])
		pr.naming_series = "_T-Purchase Receipt-"
		pr.insert()
		pr.submit()

	def _insert_delivery_note(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import test_records \
			as dn_test_records
		dn = frappe.copy_doc(dn_test_records[0])
		dn.naming_series = "_T-Delivery Note-"
		dn.insert()
		dn.submit()
		return dn

	def test_sales_invoice_with_advance(self):
		from erpnext.accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records

		jv = frappe.copy_doc(jv_test_records[0])
		jv.insert()
		jv.submit()

		si = frappe.copy_doc(test_records[0])
		si.append("advance_adjustment_details", {
			"doctype": "Sales Invoice Advance",
			"journal_voucher": jv.name,
			"jv_detail_no": jv.get("entries")[0].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.remark
		})
		si.insert()
		si.submit()
		si.load_from_db()

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s""", si.name))

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s and credit=300""", si.name))

		self.assertEqual(si.outstanding_amount, 261.8)

		si.cancel()

		self.assertTrue(not frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s""", si.name))

	def test_recurring_invoice(self):
		from frappe.utils import get_first_day, get_last_day, add_to_date, nowdate, getdate
		from erpnext.accounts.utils import get_fiscal_year
		today = nowdate()
		base_si = frappe.copy_doc(test_records[0])
		base_si.update({
			"convert_into_recurring_invoice": 1,
			"recurring_type": "Monthly",
			"notification_email_address": "test@example.com, test1@example.com, test2@example.com",
			"repeat_on_day_of_month": getdate(today).day,
			"posting_date": today,
			"due_date": None,
			"fiscal_year": get_fiscal_year(today)[0],
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(today)
		})

		# monthly
		si1 = frappe.copy_doc(base_si)
		si1.insert()
		si1.submit()
		self._test_recurring_invoice(si1, True)

		# monthly without a first and last day period
		si2 = frappe.copy_doc(base_si)
		si2.update({
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, days=30)
		})
		si2.insert()
		si2.submit()
		self._test_recurring_invoice(si2, False)

		# quarterly
		si3 = frappe.copy_doc(base_si)
		si3.update({
			"recurring_type": "Quarterly",
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(add_to_date(today, months=3))
		})
		si3.insert()
		si3.submit()
		self._test_recurring_invoice(si3, True)

		# quarterly without a first and last day period
		si4 = frappe.copy_doc(base_si)
		si4.update({
			"recurring_type": "Quarterly",
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, months=3)
		})
		si4.insert()
		si4.submit()
		self._test_recurring_invoice(si4, False)

		# yearly
		si5 = frappe.copy_doc(base_si)
		si5.update({
			"recurring_type": "Yearly",
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(add_to_date(today, years=1))
		})
		si5.insert()
		si5.submit()
		self._test_recurring_invoice(si5, True)

		# yearly without a first and last day period
		si6 = frappe.copy_doc(base_si)
		si6.update({
			"recurring_type": "Yearly",
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, years=1)
		})
		si6.insert()
		si6.submit()
		self._test_recurring_invoice(si6, False)

		# change posting date but keep recuring day to be today
		si7 = frappe.copy_doc(base_si)
		si7.update({
			"posting_date": add_to_date(today, days=-1)
		})
		si7.insert()
		si7.submit()

		# setting so that _test function works
		si7.posting_date = today
		self._test_recurring_invoice(si7, True)

	def _test_recurring_invoice(self, base_si, first_and_last_day):
		from frappe.utils import add_months, get_last_day
		from erpnext.accounts.doctype.sales_invoice.sales_invoice \
			import manage_recurring_invoices, get_next_date

		no_of_months = ({"Monthly": 1, "Quarterly": 3, "Yearly": 12})[base_si.recurring_type]

		def _test(i):
			self.assertEquals(i+1, frappe.db.sql("""select count(*) from `tabSales Invoice`
				where recurring_id=%s and docstatus=1""", base_si.recurring_id)[0][0])

			next_date = get_next_date(base_si.posting_date, no_of_months,
				base_si.repeat_on_day_of_month)

			manage_recurring_invoices(next_date=next_date, commit=False)

			recurred_invoices = frappe.db.sql("""select name from `tabSales Invoice`
				where recurring_id=%s and docstatus=1 order by name desc""",
				base_si.recurring_id)

			self.assertEquals(i+2, len(recurred_invoices))

			new_si = frappe.get_doc("Sales Invoice", recurred_invoices[0][0])

			for fieldname in ["convert_into_recurring_invoice", "recurring_type",
				"repeat_on_day_of_month", "notification_email_address"]:
					self.assertEquals(base_si.get(fieldname),
						new_si.get(fieldname))

			self.assertEquals(new_si.posting_date, unicode(next_date))

			self.assertEquals(new_si.invoice_period_from_date,
				unicode(add_months(base_si.invoice_period_from_date, no_of_months)))

			if first_and_last_day:
				self.assertEquals(new_si.invoice_period_to_date,
					unicode(get_last_day(add_months(base_si.invoice_period_to_date,
						no_of_months))))
			else:
				self.assertEquals(new_si.invoice_period_to_date,
					unicode(add_months(base_si.invoice_period_to_date, no_of_months)))


			return new_si

		# if yearly, test 1 repetition, else test 5 repetitions
		count = 1 if (no_of_months == 12) else 5
		for i in xrange(count):
			base_si = _test(i)

	def clear_stock_account_balance(self):
		frappe.db.sql("delete from `tabStock Ledger Entry`")
		frappe.db.sql("delete from tabBin")
		frappe.db.sql("delete from `tabGL Entry`")

	def test_serialized(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		se = make_serialized_item()
		serial_nos = get_serial_nos(se.get("mtn_details")[0].serial_no)

		si = frappe.copy_doc(test_records[0])
		si.update_stock = 1
		si.get("entries")[0].item_code = "_Test Serialized Item With Series"
		si.get("entries")[0].qty = 1
		si.get("entries")[0].serial_no = serial_nos[0]
		si.insert()
		si.submit()

		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "status"), "Delivered")
		self.assertFalse(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"))
		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0],
			"delivery_document_no"), si.name)

		return si

	def test_serialized_cancel(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
		si = self.test_serialized()
		si.cancel()

		serial_nos = get_serial_nos(si.get("entries")[0].serial_no)

		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "status"), "Available")
		self.assertEquals(frappe.db.get_value("Serial No", serial_nos[0], "warehouse"), "_Test Warehouse - _TC")
		self.assertFalse(frappe.db.get_value("Serial No", serial_nos[0],
			"delivery_document_no"))

	def test_serialize_status(self):
		from erpnext.stock.doctype.serial_no.serial_no import SerialNoStatusError, get_serial_nos
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item()
		serial_nos = get_serial_nos(se.get("mtn_details")[0].serial_no)

		sr = frappe.get_doc("Serial No", serial_nos[0])
		sr.status = "Not Available"
		sr.save()

		si = frappe.copy_doc(test_records[0])
		si.update_stock = 1
		si.get("entries")[0].item_code = "_Test Serialized Item With Series"
		si.get("entries")[0].qty = 1
		si.get("entries")[0].serial_no = serial_nos[0]
		si.insert()

		self.assertRaises(SerialNoStatusError, si.submit)

test_dependencies = ["Journal Voucher", "Contact", "Address"]
test_records = frappe.get_test_records('Sales Invoice')
