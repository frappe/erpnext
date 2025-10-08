# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
import frappe

# test_records = frappe.get_test_records('Mode of Payment')


class TestModeofPayment(unittest.TestCase):
	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()
  
	def test_mode_of_payment_in_payment_entry_TC_ACC_105(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		# Step 1: Get the account for the selected mode of payment (Cash)
		paid_from = get_bank_cash_account("Cash", "_Test Company").get('account')

		# Step 2: Create the payment entry and link it to the correct bank/cash account
		pe = create_payment_entry(paid_from=paid_from)

		# Step 3: Set the mode of payment to 'Cash'
		pe.mode_of_payment = "Cash"
		pe.save()

		# Step 4: Submit the payment entry
		pe.submit()

		# Step 5: Verify that the correct account head in the ledger is affected
		# Fetch ledger entries related to the payment entry
		ledger_entries = frappe.db.sql(
			"""select account, debit, credit, against_voucher
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			pe.name,
			as_dict=1,
		)

		
		# Check if the ledger entry contains the correct account
		self.assertTrue(
			any(entry.account == paid_from for entry in ledger_entries),
			f"The 'Cash' account ({paid_from}) was not affected in the ledger as expected."
		)

		# Optionally, you can also verify the amount, debit/credit, and other details of the ledger entries
		for entry in ledger_entries:
			if entry.account == paid_from:
				# Here we can add further checks, like verifying the amount and whether it's debit/credit
				self.assertEqual(entry.credit, pe.paid_amount)  # Assuming full payment is being made in Cash
    
	def test_validate_pos_mode_of_payment_TC_ACC_348(self):
		from frappe import _
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company, make_test_item
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		create_company("_Test Company")

		create_account(
			account_name="_Test Cash",
			account_type="Cash",
			company="_Test Company",
			parent_account="Cash In Hand - _TC",
			account_currency="INR"
		)
		create_warehouse(warehouse_name = "_Test Warehouse", company = "_Test Company")
		create_cost_center(cost_center_name="_Test Cost Center", company= "_Test Company")
		make_test_item(item_name="_Test Item")

		mop = frappe.new_doc("Mode of Payment")
		mop.mode_of_payment = "Test MOP Throws"
		mop.enabled = 0
		mop.type = "Cash"
		mop.append("accounts", {
			"company": "_Test Company",
			"default_account": "_Test Cash - _TC"
		})
		mop.insert(ignore_permissions=True)

		pos_profile = frappe.new_doc("POS Profile")
		pos_profile.name = "Test POS Throw"
		pos_profile.company = "_Test Company"
		pos_profile.write_off_account = "_Test Cash - _TC"
		pos_profile.warehouse = "_Test Warehouse - _TC"
		pos_profile.write_off_cost_center = "_Test Cost Center - _TC"
		pos_profile.append("payments", {
			"mode_of_payment": mop.name,
			"default": 1
		})
		pos_profile.insert(ignore_permissions=True)

		si = frappe.new_doc("Sales Invoice")
		si.company = "_Test Company"
		si.customer = "_Test Customer"
		si.is_pos = 1
		si.pos_profile = pos_profile.name
		si.currency = "INR"
		si.debit_to = "Debtors - _TC"
		si.append("items", {
			"item_code": "_Test Item",
			"qty": 1,
			"rate": 100
		})
		si.append("payments", {
			"mode_of_payment": mop.name,
			"amount": 100
		})
		si.save(ignore_permissions=True)
		si.submit()

		with self.assertRaises(frappe.ValidationError) as cm:
			mop.validate_pos_mode_of_payment()
   
	def test_validate_accounts_TC_ACC_349(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.accounts.doctype.account.test_account import create_account
		import frappe
		from frappe.exceptions import ValidationError

		# Create company and accounts
		create_company("_Test Company 1")
		create_company("_Test Company 2")

		account_a = create_account(
			account_name="_Test Cash 1",
			account_type="Cash",
			company="_Test Company 1",
			parent_account="Cash In Hand - _TC1",
			account_currency="INR"
		)
	
		mop = frappe.new_doc("Mode of Payment")
		mop.mode_of_payment = "Test MOP Validate Accounts"

		mop.append("accounts", {
			"company": "_Test Company 1",
			"default_account": account_a
		})

		mop.validate_accounts()  
		
		mop.accounts = []
		mop.append("accounts", {
			"company": "_Test Company 2",
			"default_account": account_a
		})
		mop.name ="Test MOP Validate Accounts"
		with self.assertRaises(frappe.ValidationError) as cm:
			mop.validate_accounts()

		self.assertEqual(
			str(cm.exception),
			f"Account {account_a} does not match with Company _Test Company 2 in Mode of Account: Test MOP Validate Accounts"
		)

def set_default_account_for_mode_of_payment(mode_of_payment, company, account):
	mode_of_payment.reload()
	if frappe.db.exists(
		"Mode of Payment Account", {"parent": mode_of_payment.mode_of_payment, "company": company}
	):
		frappe.db.set_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment.mode_of_payment, "company": company},
			"default_account",
			account,
		)
		return

	mode_of_payment.append("accounts", {"company": company, "default_account": account})
	mode_of_payment.save()