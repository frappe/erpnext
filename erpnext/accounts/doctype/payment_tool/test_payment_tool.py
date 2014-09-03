# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest, frappe, json
from frappe.utils import flt

class TestJournalVoucher(unittest.TestCase):
	def test_make_journal_voucher(self):
		from erpnext.accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records
		from erpnext.selling.doctype.sales_order.test_sales_order \
			import test_records as so_test_records
		from erpnext.buying.doctype.purchase_order.test_purchase_order \
			import test_records as po_test_records
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice \
			import test_records as si_test_records
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice \
			import test_records as pi_test_records

		self.clear_table_entries()

		base_customer_jv = frappe.copy_doc(jv_test_records[2])
		base_customer_jv.insert()
		base_customer_jv.submit()

		base_supplier_jv = frappe.copy_doc(jv_test_records[1])
		base_supplier_jv.insert()
		base_supplier_jv.submit()

		so = frappe.copy_doc(so_test_records[0])
		so.insert()
		so.submit()

		po = frappe.copy_doc(po_test_records[0])
		po.insert()
		po.submit()

		si = frappe.copy_doc(si_test_records[0])
		si.insert()
		si.submit()

		pi = frappe.copy_doc(pi_test_records[0])
		pi.insert()
		pi.submit()

		self.make_voucher_for_customer()
		self.make_voucher_for_supplier()

	def make_voucher_for_supplier(self):
		#Make Journal Voucher for Supplier
		payment_tool_doc = frappe.new_doc("Payment Tool")

		payment_tool_doc.set("company", "_Test Company")
		payment_tool_doc.set("party_type", "Supplier")
		payment_tool_doc.set("customer", "_Test Supplier")
		payment_tool_doc.set("received_or_paid", "Paid")
		payment_tool_doc.set("party_account", "_Test Supplier - _TC")

		payment_tool_doc.set("payment_mode", "Cheque")
		payment_tool_doc.set("payment_account", "_Test Account Bank Account - _TC")
		payment_tool_doc.set("reference_no", "123456")
		payment_tool_doc.set("reference_date", "2013-02-14")

		args = {"company": "_Test Company",
			"party_type": "Supplier",
			"received_or_paid": "Paid",
			"party_name": "_Test Supplier",
			"party_account": "_Test Supplier - _TC"
		}

		self.check_new_voucher(payment_tool_doc, args)

	def make_voucher_for_customer(self):
		#Make Journal Voucher for Customer
		payment_tool_doc = frappe.new_doc("Payment Tool")

		payment_tool_doc.set("company", "_Test Company")
		payment_tool_doc.set("party_type", "Customer")
		payment_tool_doc.set("customer", "_Test Customer")
		payment_tool_doc.set("received_or_paid", "Received")
		payment_tool_doc.set("party_account", "_Test Customer - _TC")

		payment_tool_doc.set("payment_mode", "Cheque")
		payment_tool_doc.set("payment_account", "_Test Account Bank Account - _TC")
		payment_tool_doc.set("reference_no", "123456")
		payment_tool_doc.set("reference_date", "2013-02-14")

		args = {"company": "_Test Company",
			"party_type": "Customer",
			"received_or_paid": "Received",
			"party_name": "_Test Customer",
			"party_account": "_Test Customer - _TC"
		}

		self.check_new_voucher(payment_tool_doc, args)

	def check_new_voucher(self, doc, args):
		from erpnext.accounts.doctype.payment_tool.payment_tool import PaymentTool, \
			get_outstanding_vouchers, get_orders_to_be_billed, get_against_voucher_amount, \
			get_party_account

		expected_values = self.set_expected_values(doc, args)
		doc.total_payment_amount = flt(300.00)
		new_jv = doc.make_journal_voucher()

		jv_entry_list = []

		for jv_entry in new_jv.get("entries"): 
			if doc.party_account == jv_entry.get("account"):
				jv_entry_list.append([
					jv_entry.get("account"),
					jv_entry.get("debit" if doc.received_or_paid=="Paid" \
									 else "credit"),
					jv_entry.get("against_jv"),
					jv_entry.get("against_invoice"),
					jv_entry.get("against_voucher"),
					jv_entry.get("against_sales_order"),
					jv_entry.get("against_purchase_order"),
				])

		for entry in jv_entry_list:
			self.assertTrue(entry in expected_values)

		if doc.reference_no:
			self.assertEquals(new_jv.get("cheque_no"), doc.reference_no)
		if doc.reference_date:
			self.assertEquals(new_jv.get("cheque_date"), doc.reference_date)

	def set_expected_values(self, doc, args):
		from erpnext.accounts.doctype.payment_tool.payment_tool import PaymentTool, \
			get_outstanding_vouchers, get_orders_to_be_billed, get_against_voucher_amount, \
			get_party_account

		outstanding_entries = get_outstanding_vouchers(json.dumps(args))
		expected_values = []

		for e in outstanding_entries:
			field_dict = {'Journal Voucher': [e.get("voucher_no"), None, None, None, None],
				'Sales Invoice': [None, e.get("voucher_no"), None, None, None],
				'Purchase Invoice': [None, None, e.get("voucher_no"), None, None],
				'Sales Order': [None, None, None, e.get("voucher_no"), None],
				'Purchase Order': [None, None, None, None, e.get("voucher_no")]
				}

			d1 = doc.append("payment_tool_details")
			d1.against_voucher_type = e.get("voucher_type")
			d1.against_voucher_no = e.get("voucher_no")
			d1.total_amount = e.get("invoice_amount")
			d1.outstanding_amount = e.get("outstanding_amount")
			d1.set("payment_amount", flt(100.00))

			expected_values.append([
				doc.get("party_account"),
				flt(100.00, 2)
				])

			expected_values[len(expected_values) - 1].extend(field_dict.get(e.get("voucher_type")))

			return expected_values

	def clear_table_entries(self):
		frappe.db.sql("""delete from `tabGL Entry`""")
		frappe.db.sql("""delete from `tabSales Order`""")
		frappe.db.sql("""delete from `tabPurchase Order`""")	
