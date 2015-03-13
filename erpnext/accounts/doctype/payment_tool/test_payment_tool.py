# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest, frappe, json
from frappe.utils import flt
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import test_records as si_test_records
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import test_records as pi_test_records
from erpnext.accounts.doctype.journal_entry.test_journal_entry import test_records as jv_test_records

test_dependencies = ["Item"]

class TestPaymentTool(unittest.TestCase):
	def test_make_journal_entry(self):
		self.clear_table_entries()
		frappe.db.set_default("currency", "INR")

		base_customer_jv = self.create_against_jv(jv_test_records[2], { "party": "_Test Customer 3"})
		base_supplier_jv = self.create_against_jv(jv_test_records[1], { "party": "_Test Supplier 1"})


		# Create SO with partial outstanding
		so1 = make_sales_order(customer="_Test Customer 3", qty=10, rate=100)
		
		self.create_against_jv(jv_test_records[0], {
			"party": "_Test Customer 3",
			"against_sales_order": so1.name,
			"is_advance": "Yes"
		})


		#Create SO with no outstanding
		so2 = make_sales_order(customer="_Test Customer 3")

		self.create_against_jv(jv_test_records[0], {
			"party": "_Test Customer 3",
			"against_sales_order": so2.name,
			"credit": 1000,
			"is_advance": "Yes"
		})

		# Purchase order
		po = create_purchase_order(supplier="_Test Supplier 1")

		#Create SI with partial outstanding
		si1 = self.create_voucher(si_test_records[0], {
			"customer": "_Test Customer 3",
			"debit_to": "_Test Receivable - _TC"
		})

		self.create_against_jv(jv_test_records[0], {
			"party": "_Test Customer 3",
			"against_invoice": si1.name
		})
		#Create SI with no outstanding
		si2 = self.create_voucher(si_test_records[0], {
			"customer": "_Test Customer 3",
			"debit_to": "_Test Receivable - _TC"
		})

		self.create_against_jv(jv_test_records[0], {
			"party": "_Test Customer 3",
			"against_invoice": si2.name,
			"credit": 561.80
		})

		pi = self.create_voucher(pi_test_records[0], {
			"supplier": "_Test Supplier 1",
			"credit_to": "_Test Payable - _TC"
		})

		#Create a dict containing properties and expected values
		expected_outstanding = {
			"Journal Entry"	: [base_customer_jv.name, 400.00],
			"Sales Invoice"		: [si1.name, 161.80],
			"Purchase Invoice"	: [pi.name, 1512.30],
			"Sales Order"		: [so1.name, 600.00],
			"Purchase Order"	: [po.name, 5000.00]
		}

		args = {
			"company": "_Test Company",
			"party_type": "Customer",
			"received_or_paid": "Received",
			"party": "_Test Customer 3",
			"party_account": "_Test Receivable - _TC",
			"payment_mode": "Cheque",
			"payment_account": "_Test Account Bank Account - _TC",
			"reference_no": "123456",
			"reference_date": "2013-02-14"
		}

		self.make_voucher_for_party(args, expected_outstanding)

		args.update({
			"party_type": "Supplier",
			"received_or_paid": "Paid",
			"party": "_Test Supplier 1",
			"party_account": "_Test Payable - _TC"
		})
		expected_outstanding["Journal Entry"] = [base_supplier_jv.name, 400.00]
		self.make_voucher_for_party(args, expected_outstanding)

	def create_voucher(self, test_record, args):
		doc = frappe.copy_doc(test_record)
		doc.update(args)
		doc.insert()
		doc.submit()
		return doc

	def create_against_jv(self, test_record, args):
		jv = frappe.copy_doc(test_record)
		jv.get("accounts")[0].update(args)
		if args.get("debit"):
			jv.get("accounts")[1].credit = args["debit"]
		elif args.get("credit"):
			jv.get("accounts")[1].debit = args["credit"]

		jv.insert()
		jv.submit()
		return jv

	def make_voucher_for_party(self, args, expected_outstanding):
		#Make Journal Entry for Party
		payment_tool_doc = frappe.new_doc("Payment Tool")
		
		for k, v in args.items():
			payment_tool_doc.set(k, v)

		self.check_outstanding_vouchers(payment_tool_doc, args, expected_outstanding)


	def check_outstanding_vouchers(self, doc, args, expected_outstanding):
		from erpnext.accounts.doctype.payment_tool.payment_tool import get_outstanding_vouchers
		outstanding_entries = get_outstanding_vouchers(json.dumps(args))

		for d in outstanding_entries:
			self.assertEquals(flt(d.get("outstanding_amount"), 2), expected_outstanding.get(d.get("voucher_type"))[1])

		self.check_jv_entries(doc, outstanding_entries, expected_outstanding)

	def check_jv_entries(self, paytool, outstanding_entries, expected_outstanding):
		for e in outstanding_entries:
			d1 = paytool.append("vouchers")
			d1.against_voucher_type = e.get("voucher_type")
			d1.against_voucher_no = e.get("voucher_no")
			d1.total_amount = e.get("invoice_amount")
			d1.outstanding_amount = e.get("outstanding_amount")
			d1.payment_amount = 100.00
		paytool.total_payment_amount = 300

		new_jv = paytool.make_journal_entry()

		#Create a list of expected values as [party account, payment against, against_jv, against_invoice,
		#against_voucher, against_sales_order, against_purchase_order]
		expected_values = [
			[paytool.party_account, paytool.party, 100.00, expected_outstanding.get("Journal Entry")[0], None, None, None, None],
			[paytool.party_account, paytool.party, 100.00, None, expected_outstanding.get("Sales Invoice")[0], None, None, None],
			[paytool.party_account, paytool.party, 100.00, None, None, expected_outstanding.get("Purchase Invoice")[0], None, None],
			[paytool.party_account, paytool.party, 100.00, None, None, None, expected_outstanding.get("Sales Order")[0], None],
			[paytool.party_account, paytool.party, 100.00, None, None, None, None, expected_outstanding.get("Purchase Order")[0]]
		]

		for jv_entry in new_jv.get("accounts"):
			if paytool.party_account == jv_entry.get("account") and paytool.party == jv_entry.get("party"):
				row = [
					jv_entry.get("account"),
					jv_entry.get("party"),
					jv_entry.get("debit" if paytool.party_type=="Supplier" else "credit"),
					jv_entry.get("against_jv"),
					jv_entry.get("against_invoice"),
					jv_entry.get("against_voucher"),
					jv_entry.get("against_sales_order"),
					jv_entry.get("against_purchase_order"),
				]
				self.assertTrue(row in expected_values)

		self.assertEquals(new_jv.get("cheque_no"), paytool.reference_no)
		self.assertEquals(new_jv.get("cheque_date"), paytool.reference_date)

	def clear_table_entries(self):
		frappe.db.sql("""delete from `tabGL Entry` where party in ("_Test Customer 3", "_Test Supplier 1")""")
		frappe.db.sql("""delete from `tabSales Order` where customer = "_Test Customer 3" """)
		frappe.db.sql("""delete from `tabPurchase Order` where supplier = "_Test Supplier 1" """)
