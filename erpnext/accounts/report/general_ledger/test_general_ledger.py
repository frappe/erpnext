# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, getdate, nowdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_ledger import general_ledger
from erpnext.accounts.report.general_ledger.general_ledger import execute
from erpnext.controllers.sales_and_purchase_return import make_return_doc


class TestGeneralLedger(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"
		self.clear_old_entries()

		self.base_filters = frappe._dict(
			{
				"company": self.company,
				"from_date": nowdate(),
				"to_date": nowdate(),
			}
		)

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

	def test_validate_filters_missing_company_and_dates_TC_ACC_390(self):
		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_filters(frappe._dict({}), {})

		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_filters(frappe._dict({"company": self.company}), {})

	def test_validate_filters_invalid_account_and_child_account_TC_ACC_391(self):
		# Create dummy account_details with child account
		account_details = {"_Invalid Account": frappe._dict({"is_group": 0})}
		filters = frappe._dict(
			{
				"company": self.company,
				"from_date": nowdate(),
				"to_date": nowdate(),
				"account": '["_Invalid Account"]',
			}
		)
		acc = frappe.get_all("Account", filters={"company": self.company, "is_group": 0}, limit=1)[0].name
		filters = frappe._dict(
			{
				"company": self.company,
				"from_date": nowdate(),
				"to_date": nowdate(),
				"account": f'["{acc}"]',
				"categorize_by": "Categorize by Account",
			}
		)
		account_details = {acc: frappe._dict({"is_group": 0})}
		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_filters(filters, account_details)

	def test_validate_filters_voucher_no_conflict_TC_ACC_392(self):
		filters = self.base_filters.copy()
		filters.update(
			{
				"voucher_no": "V123",
				"categorize_by": "Categorize by Voucher",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_filters(filters, {})

	def test_validate_filters_date_order_TC_ACC_393(self):
		filters = self.base_filters.copy()
		filters.from_date = add_days(nowdate(), 1)
		filters.to_date = nowdate()
		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_filters(filters, {})

	def test_validate_party_invalid_TC_ACC_394(self):
		filters = self.base_filters.copy()
		filters.party_type = "Customer"
		filters.party = ["_NonExistentCustomer"]
		with self.assertRaises(frappe.ValidationError):
			general_ledger.validate_party(filters)

	def test_set_account_currency_TC_ACC_395(self):
		acc = frappe.get_all("Account", filters={"company": self.company, "is_group": 0}, limit=1)[0].name
		filters = self.base_filters.copy()
		filters.account = [acc]
		updated = general_ledger.set_account_currency(filters)
		self.assertIn("account_currency", updated)

		cust = frappe.get_all("Customer", limit=1)[0].name
		filters = self.base_filters.copy()
		filters.party_type = "Customer"
		filters.party = [cust]
		updated = general_ledger.set_account_currency(filters)
		self.assertIn("account_currency", updated)

		accs = frappe.get_all(
			"Account",
			filters={"company": self.company, "is_group": 0, "account_currency": "INR"},
			fields=["name"],
			limit=2,
		)
		if len(accs) < 2:
			self.skipTest("Need at least 2 INR accounts for this test")

		acc_names = [a.name for a in accs]

		filters = self.base_filters.copy()
		filters.account = acc_names

		updated = general_ledger.set_account_currency(filters)

		self.assertEqual(updated.account_currency, "INR")

	# def test_get_conditions_branches_TC_ACC_396(self):
	# 	# ---------- monkeypatches ----------
	# 	orig_get_single_value = frappe.db.get_single_value
	# 	orig_get_all = frappe.db.get_all
	# 	from frappe.desk import reportview
	# 	orig_bmc = reportview.build_match_conditions
	# 	orig_get_acc_dims = general_ledger.get_accounting_dimensions
	# 	orig_get_dim_children = general_ledger.get_dimension_with_children
	# 	orig_get_cc_children = general_ledger.get_cost_centers_with_children
	# 	orig_get_cached_value = frappe.get_cached_value

	# 	frappe.db.get_single_value = lambda doctype, field: (
	# 		0 if (doctype == "Accounts Settings" and field == "ignore_is_opening_check_for_reporting") else None
	# 	)
	# 	frappe.db.get_all = lambda *a, **k: []
	# 	reportview.build_match_conditions = lambda doctype: ""
	# 	from types import SimpleNamespace
	# 	general_ledger.get_accounting_dimensions = lambda as_list=False: [
	# 		SimpleNamespace(fieldname="dim_non_tree", label="Dim NonTree", document_type="NonTreeDoc", disabled=0),
	# 		SimpleNamespace(fieldname="dim_tree", label="Dim Tree", document_type="TreeDoc", disabled=0),
	# 	]
	# 	general_ledger.get_dimension_with_children = lambda dt, vals: ["T1", "T1-1"]
	# 	general_ledger.get_cost_centers_with_children = lambda vals: ["_Test Cost Center - _TC"]
	# 	frappe.get_cached_value = lambda doctype, name, field: (
	# 		1 if (doctype == "DocType" and name == "TreeDoc" and field == "is_tree") else 0
	# 	)

	# 	try:
	# 		filters = frappe._dict({
	# 			"company": self.company,
	# 			"from_date": nowdate(),
	# 			"to_date": nowdate(),

	# 			# uncovered branches
	# 			"cost_center": ["_Test Cost Center - _TC"],
	# 			"voucher_no": "VNO-001",
	# 			"against_voucher_no": "AGV-001",
	# 			"categorize_by": "Categorize by Party",
	# 			"project": ["_Test Project"],
	# 			"include_default_book_entries": 1,
	# 			"finance_book": "FB1",
	# 			"company_fb": "FB1",
	# 			"dim_non_tree": ["NT1", "NT2"],
	# 			"dim_tree": ["T1"],
	# 		})

	# 		cond = general_ledger.get_conditions(filters)

	# 		# Assertions for all uncovered lines:
	# 		self.assertIn("cost_center in %(cost_center)s", cond)
	# 		self.assertIn("voucher_no=%(voucher_no)s", cond)
	# 		self.assertIn("against_voucher=%(against_voucher_no)s", cond)
	# 		self.assertIn("party_type in ('Customer', 'Supplier')", cond)
	# 		self.assertIn("project in %(project)s", cond)
	# 		self.assertIn("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)", cond)
	# 		self.assertIn("dim_non_tree in %(dim_non_tree)s", cond)
	# 		self.assertIn("dim_tree in %(dim_tree)s", cond)

	# 		# also ensure tree dim list got expanded by our monkeypatch
	# 		self.assertEqual(filters.dim_tree, ["T1", "T1-1"])

	# 	finally:
	# 		# restore patches
	# 		frappe.db.get_single_value = orig_get_single_value
	# 		frappe.db.get_all = orig_get_all
	# 		reportview.build_match_conditions = orig_bmc
	# 		general_ledger.get_accounting_dimensions = orig_get_acc_dims
	# 		general_ledger.get_dimension_with_children = orig_get_dim_children
	# 		general_ledger.get_cost_centers_with_children = orig_get_cc_children
	# 		frappe.get_cached_value = orig_get_cached_value

	def test_get_conditions_throws_finance_book_mismatch_TC_ACC_397(self):
		# include_default_book_entries + finance_book != company_fb -> throws
		from frappe.desk import reportview

		orig_get_single_value = frappe.db.get_single_value
		orig_bmc = reportview.build_match_conditions
		frappe.db.get_single_value = lambda *a, **k: 0
		reportview.build_match_conditions = lambda doctype: ""
		try:
			filters = frappe._dict(
				{
					"company": self.company,
					"from_date": nowdate(),
					"to_date": nowdate(),
					"include_default_book_entries": 1,
					"finance_book": "FB2",
					"company_fb": "FB1",
				}
			)
			with self.assertRaises(frappe.ValidationError):
				general_ledger.get_conditions(filters)
		finally:
			frappe.db.get_single_value = orig_get_single_value
			reportview.build_match_conditions = orig_bmc

	def test_get_conditions_include_default_finance_book_without_TC_ACC_398(self):
		from frappe.desk import reportview

		orig_get_single_value = frappe.db.get_single_value
		orig_bmc = reportview.build_match_conditions
		frappe.db.get_single_value = lambda *a, **k: 0
		reportview.build_match_conditions = lambda doctype: ""
		try:
			filters = frappe._dict(
				{
					"company": self.company,
					"from_date": nowdate(),
					"to_date": nowdate(),
					"finance_book": "FBX",
				}
			)
			cond = general_ledger.get_conditions(filters)
			self.assertIn("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)", cond)
		finally:
			frappe.db.get_single_value = orig_get_single_value
			reportview.build_match_conditions = orig_bmc

	def test_get_data_with_opening_closing_TC_ACC_399(self):
		# patch
		orig_get_single_value = frappe.db.get_single_value
		frappe.db.get_single_value = (
			lambda doctype, field: 0
			if (doctype == "Accounts Settings" and field == "enable_immutable_ledger")
			else None
		)

		try:
			filters = frappe._dict(
				{
					"company": self.company,
					"from_date": nowdate(),
					"to_date": nowdate(),
					"categorize_by": "Categorize by Account",
				}
			)

			gl_entries = [
				frappe._dict(
					{
						"gl_entry": "GLE-1",
						"posting_date": getdate(nowdate()),
						"account": "Cash - _TC",
						"party_type": None,
						"party": None,
						"voucher_type": "Journal Entry",
						"voucher_subtype": None,
						"voucher_no": "JV-1",
						"cost_center": None,
						"project": None,
						"against_voucher_type": None,
						"against_voucher": None,
						"account_currency": "INR",
						"against": "Bank - _TC",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 100.0,
						"credit": 0.0,
						"debit_in_account_currency": 100.0,
						"credit_in_account_currency": 0.0,
					}
				),
				frappe._dict(
					{
						"gl_entry": "GLE-2",
						"posting_date": getdate(nowdate()),
						"account": "Cash - _TC",
						"party_type": None,
						"party": None,
						"voucher_type": "Journal Entry",
						"voucher_subtype": None,
						"voucher_no": "JV-2",
						"cost_center": None,
						"project": None,
						"against_voucher_type": None,
						"against_voucher": None,
						"account_currency": "INR",
						"against": "Bank - _TC",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 0.0,
						"credit": 40.0,
						"debit_in_account_currency": 0.0,
						"credit_in_account_currency": 40.0,
					}
				),
			]

			data = general_ledger.get_data_with_opening_closing(
				filters=filters,
				account_details={},
				accounting_dimensions=[],
				gl_entries=gl_entries,
			)

			self.assertEqual(data[0].get("account"), "'Opening'")

			# 1) a separator row before entries (only the two keys with None)
			sep_rows = [
				d
				for d in data
				if set(d.keys()) == {"debit_in_transaction_currency", "credit_in_transaction_currency"}
				and d["debit_in_transaction_currency"] is None
				and d["credit_in_transaction_currency"] is None
			]
			self.assertGreaterEqual(len(sep_rows), 2)

			# 2) per-account opening appended by the inner condition
			opening_rows = [d for d in data if d.get("account") == "'Opening'"]
			self.assertGreaterEqual(len(opening_rows), 2)
			# 3) our entries show up
			self.assertTrue(any(d.get("voucher_no") == "JV-1" for d in data))
			self.assertTrue(any(d.get("voucher_no") == "JV-2" for d in data))

			total_rows = [d for d in data if d.get("account") == "'Total'"]
			self.assertGreaterEqual(len(total_rows), 2)

			closing_rows = [d for d in data if d.get("account") == "'Closing (Opening + Total)'"]
			self.assertGreaterEqual(len(closing_rows), 2)
		finally:
			frappe.db.get_single_value = orig_get_single_value

	def test_get_accountwise_gle_consolidated_txn_currency_and_net_values_TC_ACC_400(self):
		"""
		Covers:
		- add_values_in_transaction_currency branch
		- show_net_values_in_party_account branch (both +ve and -ve net)
		- against_voucher concatenation
		- consolidated path (not using gle_map.entries)
		"""
		# Monkeypatch: avoid singleton/doctypes noise
		orig_get_single_value = frappe.db.get_single_value
		orig_get_account_type_map = general_ledger.get_account_type_map

		# immutable_ledger = 0 so 'creation' is NOT part of consolidated key → rows consolidate
		frappe.db.get_single_value = (
			lambda doctype, field: 0
			if (doctype == "Accounts Settings" and field == "enable_immutable_ledger")
			else None
		)

		# Force account types so the "net" logic is executed
		general_ledger.get_account_type_map = lambda company: frappe._dict(
			{
				"Test Debtors - _TC": "Receivable",
				"Test Payable - _TC": "Payable",
			}
		)

		try:
			filters = frappe._dict(
				{
					"company": "_Test Company",
					"from_date": nowdate(),
					"to_date": nowdate(),
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"add_values_in_transaction_currency": 1,
					"show_net_values_in_party_account": 1,
				}
			)

			# Two consolidated keys (SI-001 and PI-001) each with two rows → triggers update_value_in_dict
			gl_entries = [
				# Key A: net positive (+20) → dr_or_cr = debit
				frappe._dict(
					{
						"gl_entry": "GLE-A1",
						"posting_date": getdate(nowdate()),
						"account": "Test Debtors - _TC",
						"party_type": "Customer",
						"party": "_Test Customer",
						"voucher_type": "Sales Invoice",
						"voucher_no": "SI-001",
						"against_voucher": "AG-1",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 50.0,
						"credit": 0.0,
						"debit_in_account_currency": 50.0,
						"credit_in_account_currency": 0.0,
						"debit_in_transaction_currency": 50.0,
						"credit_in_transaction_currency": 0.0,
					}
				),
				frappe._dict(
					{
						"gl_entry": "GLE-A2",
						"posting_date": getdate(nowdate()),
						"account": "Test Debtors - _TC",
						"party_type": "Customer",
						"party": "_Test Customer",
						"voucher_type": "Sales Invoice",
						"voucher_no": "SI-001",
						"against_voucher": "AG-2",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 50.0,
						"credit": 40.0,
						"debit_in_account_currency": 50.0,
						"credit_in_account_currency": 40.0,
						"debit_in_transaction_currency": 50.0,
						"credit_in_transaction_currency": 40.0,
					}
				),
				# Key B: net negative (-80) → dr_or_cr = credit
				frappe._dict(
					{
						"gl_entry": "GLE-B1",
						"posting_date": getdate(nowdate()),
						"account": "Test Payable - _TC",
						"party_type": "Supplier",
						"party": "_Test Supplier",
						"voucher_type": "Purchase Invoice",
						"voucher_no": "PI-001",
						"against_voucher": "PG-1",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 10.0,
						"credit": 0.0,
						"debit_in_account_currency": 10.0,
						"credit_in_account_currency": 0.0,
						"debit_in_transaction_currency": 10.0,
						"credit_in_transaction_currency": 0.0,
					}
				),
				frappe._dict(
					{
						"gl_entry": "GLE-B2",
						"posting_date": getdate(nowdate()),
						"account": "Test Payable - _TC",
						"party_type": "Supplier",
						"party": "_Test Supplier",
						"voucher_type": "Purchase Invoice",
						"voucher_no": "PI-001",
						"against_voucher": "PG-2",
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 0.0,
						"credit": 90.0,
						"debit_in_account_currency": 0.0,
						"credit_in_account_currency": 90.0,
						"debit_in_transaction_currency": 0.0,
						"credit_in_transaction_currency": 90.0,
					}
				),
			]

			totals_dict = general_ledger.get_totals_dict()
			gle_map = general_ledger.initialize_gle_map(gl_entries, filters, totals_dict)

			totals, entries = general_ledger.get_accountwise_gle(
				filters, [], gl_entries, gle_map, totals_dict
			)

			# We should get one consolidated row per key
			self.assertEqual(len(entries), 2)

			si = next(x for x in entries if x.voucher_no == "SI-001")
			self.assertEqual(si.debit, 60.0)
			self.assertEqual(si.credit, 0.0)
			# Transaction currency sums added (no netting here)
			self.assertEqual(si.debit_in_transaction_currency, 100.0)
			self.assertEqual(si.credit_in_transaction_currency, 40.0)
			# Against voucher concatenated
			self.assertIn("AG-1, AG-2", si.against_voucher)
			# Net in account currency also matches 60
			self.assertEqual(si.debit_in_account_currency, 60.0)
			self.assertEqual(si.credit_in_account_currency, 0.0)

			# Find PI-001 (net -80 → credit=80, debit=0)
			pi = next(x for x in entries if x.voucher_no == "PI-001")
			self.assertEqual(pi.debit, 0.0)
			self.assertEqual(pi.credit, 80.0)
			self.assertEqual(pi.debit_in_transaction_currency, 10.0)
			self.assertEqual(pi.credit_in_transaction_currency, 90.0)
			self.assertIn("PG-1, PG-2", pi.against_voucher)

			# Totals should include consolidated values
			self.assertGreater(totals.total.debit + totals.total.credit, 0)

		finally:
			frappe.db.get_single_value = orig_get_single_value
			general_ledger.get_account_type_map = orig_get_account_type_map

	def test_get_accountwise_gle_non_consolidated_opening_and_total_paths_TC_ACC_401(self):
		"""
		Covers:
		- posting_date < from_date (opening path)
		- posting_date <= to_date (total path)
		- not group_by_voucher_consolidated → updates gle_map and totals
		- appends to gle_map[group_by_value].entries
		"""
		# immutable_ledger lookup harmless; just stub it
		orig_get_single_value = frappe.db.get_single_value
		frappe.db.get_single_value = (
			lambda doctype, field: 0
			if (doctype == "Accounts Settings" and field == "enable_immutable_ledger")
			else None
		)

		try:
			from_dt = nowdate()
			to_dt = from_dt

			filters = frappe._dict(
				{
					"company": "_Test Company",
					"from_date": from_dt,
					"to_date": to_dt,
					"categorize_by": None,  # → group_by_field = 'voucher_no' (non-consolidated path)
					"show_opening_entries": 0,
				}
			)

			gl_entries = [
				# OLD: before from_date → opening
				frappe._dict(
					{
						"gl_entry": "GLE-OLD",
						"posting_date": getdate(add_days(from_dt, -1)),
						"account": "Cash - _TC",
						"party_type": None,
						"party": None,
						"voucher_type": "Journal Entry",
						"voucher_no": "JV-OLD",
						"against_voucher": None,
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 70.0,
						"credit": 0.0,
						"debit_in_account_currency": 70.0,
						"credit_in_account_currency": 0.0,
					}
				),
				# IN: on to_date → total + appended to gle_map entries
				frappe._dict(
					{
						"gl_entry": "GLE-IN",
						"posting_date": getdate(to_dt),
						"account": "Cash - _TC",
						"party_type": None,
						"party": None,
						"voucher_type": "Journal Entry",
						"voucher_no": "JV-IN",
						"against_voucher": None,
						"is_opening": "No",
						"creation": nowdate(),
						"debit": 0.0,
						"credit": 25.0,
						"debit_in_account_currency": 0.0,
						"credit_in_account_currency": 25.0,
					}
				),
			]

			totals_dict = general_ledger.get_totals_dict()
			gle_map = general_ledger.initialize_gle_map(gl_entries, filters, totals_dict)

			totals, entries = general_ledger.get_accountwise_gle(
				filters, [], gl_entries, gle_map, totals_dict
			)

			# Non-consolidated → returned 'entries' list is empty
			self.assertEqual(entries, [])

			# Opening totals include OLD entry
			self.assertEqual(totals.opening.debit, 70.0)
			self.assertEqual(totals.opening.credit, 0.0)

			# Total totals include IN entry
			self.assertEqual(totals.total.debit, 0.0)
			self.assertEqual(totals.total.credit, 25.0)

			# gle_map side-effects:
			# - JV-OLD: only affected totals (no entries appended)
			self.assertEqual(len(gle_map["JV-OLD"].entries), 0)
			# - JV-IN: entry appended
			self.assertEqual(len(gle_map["JV-IN"].entries), 1)
			self.assertEqual(gle_map["JV-IN"].entries[0].gl_entry, "GLE-IN")

		finally:
			frappe.db.get_single_value = orig_get_single_value
