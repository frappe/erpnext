# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import qb
from frappe.utils import flt, today

from erpnext.accounts.doctype.party_link.party_link import create_party_link
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.party import get_party_account
from erpnext.accounts.report.general_ledger.general_ledger import execute
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite


class TestGeneralLedger(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.clear_old_entries()

	def clear_old_entries(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def _make_setoff_jv(self, company, customer, supplier, amount, posting_date):
		"""Explicitly create a CPA set-off Journal Entry with is_system_generated=1."""
		customer_account = get_party_account("Customer", customer, company)
		supplier_account = get_party_account("Supplier", supplier, company)

		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.posting_date = posting_date
		jv.company = company
		jv.is_system_generated = 1
		jv.remark = "Test CPA set-off JV"
		jv.append(
			"accounts",
			{
				"account": customer_account,
				"party_type": "Customer",
				"party": customer,
				"credit_in_account_currency": amount,
			},
		)
		jv.append(
			"accounts",
			{
				"account": supplier_account,
				"party_type": "Supplier",
				"party": supplier,
				"debit_in_account_currency": amount,
			},
		)
		jv.save()
		jv.submit()
		return jv

	def test_cpa_includes_linked_party_entries(self):
		"""
		CPA support: filtering GL by a Customer should also return GL entries posted under the linked Supplier (and vice versa) via Party Link.
		"""
		company = self.company
		customer = "_Test Customer"
		supplier = "_Test Supplier"

		# clean up any existing Party Link involving either party on either side
		if pl_name := frappe.get_all(
			"Party Link",
			or_filters=[
				["primary_party", "in", [customer, supplier]],
				["secondary_party", "in", [customer, supplier]],
			],
			pluck="name",
			limit=1,
		):
			frappe.delete_doc("Party Link", pl_name[0], ignore_permissions=True)

		party_link = create_party_link(
			primary_role="Customer",
			primary_party=customer,
			secondary_party=supplier,
		)

		try:
			# GL entry via Sales Invoice (Customer side)
			si = create_sales_invoice(customer=customer, company=company, do_not_submit=False)

			# GL entry via Purchase Invoice (Supplier side)
			pi = make_purchase_invoice(supplier=supplier, company=company)

			# Explicitly create a CPA set-off JV so the exclusion test is not relying on auto-creation
			setoff_jv = self._make_setoff_jv(
				company, customer, supplier, si.outstanding_amount, si.posting_date
			)

			# Filter by Customer only — should include both Customer and Supplier entries
			_, data = execute(
				frappe._dict(
					{
						"company": company,
						"from_date": si.posting_date,
						"to_date": si.posting_date,
						"party_type": "Customer",
						"party": [customer],
					}
				)
			)

			party_types_in_result = {row.party_type for row in data if row.get("party_type")}
			self.assertIn("Customer", party_types_in_result)
			self.assertIn("Supplier", party_types_in_result)
			# The explicitly created set-off JV must not appear in GL results
			voucher_nos = {row.voucher_no for row in data if row.get("voucher_no")}
			self.assertNotIn(setoff_jv.name, voucher_nos, "CPA set-off JV should be excluded from GL results")

			# Filter by Supplier only — should include both sides too
			_, data = execute(
				frappe._dict(
					{
						"company": company,
						"from_date": pi.posting_date,
						"to_date": pi.posting_date,
						"party_type": "Supplier",
						"party": [supplier],
					}
				)
			)

			party_types_in_result = {row.party_type for row in data if row.get("party_type")}
			self.assertIn("Customer", party_types_in_result)
			self.assertIn("Supplier", party_types_in_result)
			voucher_nos = {row.voucher_no for row in data if row.get("voucher_no")}
			self.assertNotIn(setoff_jv.name, voucher_nos, "CPA set-off JV should be excluded from GL results")
		finally:
			frappe.delete_doc("Party Link", party_link.name, ignore_permissions=True)

	def test_party_filter_without_party_link(self):
		"""
		When a party has no Party Link, GL filtering should only return entries for that party — no cross-party leakage.
		"""
		company = self.company
		customer = "_Test Customer"
		other_customer = "_Test Customer 1"

		# Ensure no Party Link exists for these parties (either side)
		if pl_name := frappe.get_all(
			"Party Link",
			or_filters=[
				["primary_party", "in", [customer, other_customer]],
				["secondary_party", "in", [customer, other_customer]],
			],
			pluck="name",
			limit=1,
		):
			frappe.delete_doc("Party Link", pl_name[0], ignore_permissions=True)

		# GL entry for customer
		si = create_sales_invoice(customer=customer, company=company, do_not_submit=False)
		# GL entry for a different customer
		create_sales_invoice(customer=other_customer, company=company, do_not_submit=False)

		_, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"party_type": "Customer",
					"party": [customer],
				}
			)
		)

		parties_in_result = {row.party for row in data if row.get("party")}
		self.assertIn(customer, parties_in_result)
		self.assertNotIn(other_customer, parties_in_result)

	def test_cpa_mixed_party_list_partial_links(self):
		"""
		Linked counterparts are included only for parties that have a Party Link; unlinked parties return only their own GL entries.
		"""
		company = self.company
		linked_customer = "_Test Customer"
		unlinked_customer = "_Test Customer 1"
		supplier = "_Test Supplier"

		# clean up any existing Party Link touching these parties
		if pl_name := frappe.get_all(
			"Party Link",
			or_filters=[
				["primary_party", "in", [linked_customer, unlinked_customer, supplier]],
				["secondary_party", "in", [linked_customer, unlinked_customer, supplier]],
			],
			pluck="name",
			limit=1,
		):
			frappe.delete_doc("Party Link", pl_name[0], ignore_permissions=True)

		party_link = create_party_link(
			primary_role="Customer",
			primary_party=linked_customer,
			secondary_party=supplier,
		)

		try:
			si_linked = create_sales_invoice(customer=linked_customer, company=company, do_not_submit=False)
			_si_unlinked = create_sales_invoice(
				customer=unlinked_customer, company=company, do_not_submit=False
			)
			make_purchase_invoice(supplier=supplier, company=company, do_not_submit=False)

			# Explicitly create a CPA set-off JV so the exclusion test is not relying on auto-creation
			setoff_jv = self._make_setoff_jv(
				company, linked_customer, supplier, si_linked.outstanding_amount, si_linked.posting_date
			)

			_, data = execute(
				frappe._dict(
					{
						"company": company,
						"from_date": si_linked.posting_date,
						"to_date": si_linked.posting_date,
						"party_type": "Customer",
						"party": [linked_customer, unlinked_customer],
					}
				)
			)

			parties_in_result = {row.party for row in data if row.get("party")}
			party_types_in_result = {row.party_type for row in data if row.get("party_type")}

			# linked_customer's own entries are present
			self.assertIn(linked_customer, parties_in_result)
			# unlinked_customer's own entries are present
			self.assertIn(unlinked_customer, parties_in_result)
			# supplier linked to linked_customer is pulled in
			self.assertIn(supplier, parties_in_result)
			self.assertIn("Supplier", party_types_in_result)
			# The explicitly created set-off JV must not appear in GL results
			voucher_nos = {row.voucher_no for row in data if row.get("voucher_no")}
			self.assertNotIn(setoff_jv.name, voucher_nos, "CPA set-off JV should be excluded from GL results")
		finally:
			frappe.delete_doc("Party Link", party_link.name, ignore_permissions=True)

	def test_foreign_account_balance_after_exchange_rate_revaluation(self):
		"""
		Checks the correctness of balance after exchange rate revaluation
		"""
		# create a new account with USD currency
		account_name = "Test USD Account for Revalutation"
		company = "_Test Company"
		account = frappe.get_doc(
			{
				"account_name": account_name,
				"is_group": 0,
				"company": company,
				"root_type": "Asset",
				"report_type": "Balance Sheet",
				"account_currency": "USD",
				"parent_account": "Bank Accounts - _TC",
				"account_type": "Bank",
				"doctype": "Account",
			}
		)
		account.insert(ignore_if_duplicate=True)
		# create a JV to debit 1000 USD at 75 exchange rate
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = company
		jv.multi_currency = 1
		jv.cost_center = "_Test Cost Center - _TC"
		jv.set(
			"accounts",
			[
				{
					"account": account.name,
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"exchange_rate": 75,
					"cost_center": "_Test Cost Center - _TC",
				},
				{
					"account": "Cash - _TC",
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 75000,
					"cost_center": "_Test Cost Center - _TC",
				},
			],
		)
		jv.save()
		jv.submit()
		# create a JV to credit 900 USD at 100 exchange rate
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = company
		jv.multi_currency = 1
		jv.cost_center = "_Test Cost Center - _TC"
		jv.set(
			"accounts",
			[
				{
					"account": account.name,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 900,
					"exchange_rate": 100,
					"cost_center": "_Test Cost Center - _TC",
				},
				{
					"account": "Cash - _TC",
					"debit_in_account_currency": 90000,
					"credit_in_account_currency": 0,
					"cost_center": "_Test Cost Center - _TC",
				},
			],
		)
		jv.save()
		jv.submit()

		# create an exchange rate revaluation entry at 77 exchange rate
		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.posting_date = today()
		revaluation.company = company
		revaluation.set(
			"accounts",
			[
				{
					"account": account.name,
					"account_currency": "USD",
					"new_exchange_rate": 77,
					"new_balance_in_base_currency": 7700,
					"balance_in_base_currency": -15000,
					"balance_in_account_currency": 100,
					"current_exchange_rate": -150,
				}
			],
		)
		revaluation.save()
		revaluation.submit()

		# post journal entry to revaluate
		frappe.db.set_value(
			"Company", company, "unrealized_exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		revaluation_jv = revaluation.make_jv_for_revaluation()
		revaluation_jv.cost_center = "_Test Cost Center - _TC"
		for acc in revaluation_jv.get("accounts"):
			acc.cost_center = "_Test Cost Center - _TC"
		revaluation_jv.save()
		revaluation_jv.submit()

		# check the balance of the account
		balance = frappe.db.sql(
			"""
				select sum(debit_in_account_currency) - sum(credit_in_account_currency)
				from `tabGL Entry`
				where account = %s
				group by account
			""",
			account.name,
		)

		self.assertEqual(balance[0][0], 100)

		# check if general ledger shows correct balance
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
				}
			)
		)

		self.assertEqual(data[1]["account"], account.name)
		self.assertEqual(data[1]["debit"], 1000)
		self.assertEqual(data[1]["credit"], 0)
		self.assertEqual(data[2]["debit"], 0)
		self.assertEqual(data[2]["credit"], 900)
		self.assertEqual(data[3]["debit"], 100)
		self.assertEqual(data[3]["credit"], 100)

	def test_ignore_exchange_rate_journals_filter(self):
		# create a new account with USD currency
		account_name = "Test Debtors USD"
		company = "_Test Company"
		account = frappe.get_doc(
			{
				"account_name": account_name,
				"is_group": 0,
				"company": company,
				"root_type": "Asset",
				"report_type": "Balance Sheet",
				"account_currency": "USD",
				"parent_account": "Accounts Receivable - _TC",
				"account_type": "Receivable",
				"doctype": "Account",
			}
		)
		account.insert(ignore_if_duplicate=True)
		# create a JV to debit 1000 USD at 75 exchange rate
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = company
		jv.multi_currency = 1
		jv.cost_center = "_Test Cost Center - _TC"
		jv.set(
			"accounts",
			[
				{
					"account": account.name,
					"party_type": "Customer",
					"party": "_Test Customer USD",
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"exchange_rate": 75,
					"cost_center": "_Test Cost Center - _TC",
				},
				{
					"account": "Cash - _TC",
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 75000,
					"cost_center": "_Test Cost Center - _TC",
				},
			],
		)
		jv.save()
		jv.submit()

		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.posting_date = today()
		revaluation.company = company
		accounts = revaluation.get_accounts_data()
		revaluation.extend("accounts", accounts)
		row = revaluation.accounts[0]
		row.new_exchange_rate = 83
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		revaluation.set_total_gain_loss()
		revaluation = revaluation.save().submit()

		# post journal entry for Revaluation doc
		frappe.db.set_value(
			"Company", company, "unrealized_exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		revaluation_jv = revaluation.make_jv_for_revaluation()
		revaluation_jv.cost_center = "_Test Cost Center - _TC"
		for acc in revaluation_jv.get("accounts"):
			acc.cost_center = "_Test Cost Center - _TC"
		revaluation_jv.save()
		revaluation_jv.submit()

		# With ignore_err enabled
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_err": True,
				}
			)
		)
		self.assertNotIn(revaluation_jv.name, set([x.voucher_no for x in data]))

		# Without ignore_err enabled
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_err": False,
				}
			)
		)
		self.assertIn(revaluation_jv.name, set([x.voucher_no for x in data]))

	def test_ignore_cr_dr_notes_filter(self):
		si = create_sales_invoice()

		cr_note = make_return_doc(si.doctype, si.name)
		cr_note.submit()

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = si.company
		pr.party_type = "Customer"
		pr.party = si.customer
		pr.receivable_payable_account = si.debit_to

		pr.get_unreconciled_entries()

		invoices = [invoice.as_dict() for invoice in pr.invoices if invoice.invoice_number == si.name]
		payments = [payment.as_dict() for payment in pr.payments if payment.reference_name == cr_note.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		system_generated_journal = frappe.db.get_all(
			"Journal Entry",
			filters={
				"docstatus": 1,
				"reference_type": si.doctype,
				"reference_name": si.name,
				"voucher_type": "Credit Note",
				"is_system_generated": True,
			},
			fields=["name"],
		)
		self.assertEqual(len(system_generated_journal), 1)
		expected = set([si.name, cr_note.name, system_generated_journal[0].name])
		# Without ignore_cr_dr_notes
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"account": [si.debit_to],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_cr_dr_notes": False,
				}
			)
		)
		actual = set([x.voucher_no for x in data if x.voucher_no])
		self.assertEqual(expected, actual)

		# Without ignore_cr_dr_notes
		expected = set([si.name, cr_note.name])
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"account": [si.debit_to],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_cr_dr_notes": True,
				}
			)
		)
		actual = set([x.voucher_no for x in data if x.voucher_no])
		self.assertEqual(expected, actual)
