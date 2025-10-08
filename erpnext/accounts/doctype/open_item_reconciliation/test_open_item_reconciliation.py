# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOpenItemReconciliation(FrappeTestCase):
	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()
  
	def test_fetch_unreconciled_gl_entries_with_real_gl_TC_ACC_329(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			create_payment_entry,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import check_gl_entries
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		# Create mock GL Entries
		company = "_Test Company"
		cost_center = "_Test Cost Center - _TC"
		create_company(company)
		create_customer(name="_Test Customer", currency="INR")
		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		account = create_account(
			account_name="Open Items",
			parent_account="Accounts Receivable - _TC",
			company=company,
			account_currency="INR",
			do_not_save=True
		)
		account.is_open_item = 1
		account.report_type = "Balance Sheet"
		account.save(ignore_permissions=True)
		create_warehouse(warehouse_name="_Test Warehouse", company=company)
		validate_fiscal_year(company)
		item = make_item("_Test Item", {"is_stock_item": 1})
		si = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=1000,
			income_account=account.name,
			do_not_submit=True
	
		)
		si.submit()
		pe = create_payment_entry(
			company=company,
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from=account.name,
			paid_to="Cash - _TC",
			paid_amount=1000
		)
		pe.save().submit()
		credit_gl = frappe.get_doc({
			"doctype": "GL Entry",
			"company": company,
			"posting_date": si.posting_date,
			"account": account.name,
			"party_type": "Customer",
			"party": "_Test Customer",
			"debit": 0,
			"credit": 1000,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": 1000,
			"voucher_type": "Sales Invoice",
			"voucher_no": si.name,
			"is_cancelled": 0,
			"is_opening": "No",
			"is_reconciled": 0,
			"cost_center": cost_center,
			"unreconciled_amount": 1000,
		})
		credit_gl.insert()
		debit_gl = frappe.get_doc({
			"doctype": "GL Entry",
			"company": company,
			"posting_date": pe.posting_date,
			"account": account.name,
			"party_type": "Customer",
			"party": "_Test Customer",
			"debit": 500,
			"credit": 0,
			"debit_in_account_currency": 500,
			"credit_in_account_currency": 0,
			"voucher_type": "Payment Entry",
			"voucher_no": pe.name,
			"is_cancelled": 0,
			"is_opening": "No",
			"is_reconciled": 0,
			"cost_center": cost_center,
			"unreconciled_amount": 500,
		})
		debit_gl.insert()

		recon = frappe.get_doc({
			"doctype": "Open Item Reconciliation",
			"company": company,
			"account": account.name,
			"party_type": "Customer",
			"party": "_Test Customer",
			"cost_center": cost_center
		})

		recon.fetch_unreconciled_gl_entries()
		self.assertEqual(recon.credit_amount[1].outstanding_amount, 1000)
		self.assertEqual(recon.credit_amount[1].voucher_type, "Sales Invoice")
		self.assertEqual(recon.credit_amount[1].voucher_no, si.name)

		self.assertEqual(len(recon.debit_amount), 1)
		self.assertEqual(recon.debit_amount[0].outstanding_amount, 500)
		self.assertEqual(recon.debit_amount[0].voucher_type, "Payment Entry")
		self.assertEqual(recon.debit_amount[0].voucher_no, pe.name)
		
	def test_remove_current_glr_row_TC_ACC_330(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			create_payment_entry,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		company = "_Test Company"
		create_company(company)
		create_customer(name="_Test Customer", currency="INR")
		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		account = create_account(
			account_name="Open Items",
			parent_account="Accounts Receivable - _TC",
			company=company,
			account_currency="INR",
			do_not_save=True
		)
		account.is_open_item = 1
		account.report_type = "Balance Sheet"
		account.save(ignore_permissions=True)
		create_warehouse("_Test Warehouse", company=company)
		item = make_item("_Test Item", {"is_stock_item": 1})

		si = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=1000,
			income_account=account.name,
			do_not_submit=True
		)
		si.submit()

		pe = create_payment_entry(
			company=company,
			payment_type="Receive",
			party_type="Customer",
			party="_Test Customer",
			paid_from=account.name,
			paid_to="Cash - _TC",
			paid_amount=1000
		)
		pe.submit()

		gl_credit= frappe.get_all("GL Entry", filters={
			"voucher_type": "Sales Invoice",
			"voucher_no": si.name,
			"account": account.name
		}, fields=["name"], limit=1)[0]
  
		gl_debit = frappe.get_all("GL Entry", filters={
			"voucher_type": "Payment Entry",
			"voucher_no": pe.name,
			"account": account.name
		}, fields=["name"], limit=1)[0]

		glr = frappe.get_doc({
			"doctype": "GL Entry Reconciliation Details",
			"gl_entry": gl_credit.name,
			"parent": gl_credit.name,
			"parentfield": "gl_entry_reconciliation_details",
			"parenttype": "GL Entry",
			"amount": 1000
		}).insert(ignore_permissions=True)
		

		frappe.db.set_value("GL Entry", gl_credit.name, "reconciled_amount", 0)
		frappe.db.set_value("GL Entry", gl_credit.name, "unreconciled_amount", 1000)
		frappe.db.set_value("GL Entry", gl_credit.name, "is_reconciled", 0)

		frappe.db.set_value("GL Entry", gl_debit.name, "reconciled_amount", 600)
		frappe.db.set_value("GL Entry", gl_debit.name, "unreconciled_amount", 400)
		frappe.db.set_value("GL Entry", gl_debit.name, "unreconciled_amount", 400)
		frappe.db.set_value("GL Entry", gl_debit.name, "credit_in_account_currency", 0)
		frappe.db.set_value("GL Entry", gl_debit.name, "debit_in_account_currency", 1000)

		recon = frappe.new_doc("Open Item Reconciliation")
		recon.remove_current_glr_row(
			reconciled_entries=[gl_credit.name],
			unwanted_lines=[]
		)
		gle_debit = frappe.get_doc("GL Entry", gl_debit.name)
		assert gle_debit.reconciled_amount == 600.0
		assert gle_debit.unreconciled_amount == 400.0
		assert gle_debit.is_reconciled == 0
		
		recon.remove_current_glr_row(
			reconciled_entries=[gl_debit.name, gl_credit.name],
			unwanted_lines=[glr.name]
		)
		
		gle_debit.reload()
  
		assert not frappe.db.exists("GL Entry Reconciliation Details", glr.name)
		self.assertEqual(gle_debit.reconciled_amount, 0.0)
		self.assertEqual(gle_debit.unreconciled_amount, 1000.0)
		self.assertEqual(gle_debit.is_reconciled, 0)

		gle_credit = frappe.get_doc("GL Entry", gl_credit.name)
		self.assertEqual(gle_credit.reconciled_amount, 0.0)
		self.assertEqual(gle_credit.unreconciled_amount, 1000.0)
		self.assertEqual(gle_credit.is_reconciled, 0)
  
	def test_reconcile_allocated_entries_with_sales_invoice_TC_ACC_331(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from frappe.utils import nowdate

		# Setup company, customer, accounts
		company = "_Test Company"
		create_company(company)
		create_customer(name="_Test Customer", currency="INR")
		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		create_warehouse("_Test Warehouse", company=company)

		# Create open item account
		account = create_account(
			account_name="Open Items",
			parent_account="Accounts Receivable - _TC",
			company=company,
			account_currency="INR",
			do_not_save=True
		)
		account.is_open_item = 1
		account.report_type = "Balance Sheet"
		account.save(ignore_permissions=True)

		# Create stock item
		item = make_item("_Test Item", {"is_stock_item": 1})

		# Create and submit Sales Invoice
		si = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=1000,
			income_account=account.name,
			do_not_submit=True
		)
		si.submit()

		# Get GL Entries for the Sales Invoice
		gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": si.name}, fields=["name", "debit_in_account_currency", "credit_in_account_currency"])
		assert len(gl_entries) >= 2

		debit_gle = next(g for g in gl_entries if g["debit_in_account_currency"] > 0)
		credit_gle = next(g for g in gl_entries if g["credit_in_account_currency"] > 0)

		# Create dummy Open Item Reconciliation doc
		recon_doc = frappe.get_doc({
			"doctype": "Open Item Reconciliation",
			"title": "Test Reconciliation",
			"account": account.name
		}).insert()

		# Call method with allocated entries
		args = {
			"allocated_entries": [{
				"credit_gl": credit_gle["name"],
				"debit_gl": debit_gle["name"],
				"allocated_amount": 1000.0
			}]
		}
		recon_doc.reconcile_allocated_entries(args)

		# Reload and validate results
		for gle_name in [credit_gle["name"], debit_gle["name"]]:
			gle = frappe.get_doc("GL Entry", gle_name)
			assert gle.reconciled_amount == 1000.0
			assert gle.unreconciled_amount == 0.0
			assert gle.is_reconciled == 1
			assert gle.gl_entry_reconciliation_details
			assert gle.gl_entry_reconciliation_details[0].gl_entry in [debit_gle["name"], credit_gle["name"]]


	def test_allocate_entries_using_real_gl_entries_TC_ACC_332(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
			create_payment_entry,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		company = "_Test Company"
		create_company(company)
		create_customer(name="_Test Customer", currency="INR")
		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		create_warehouse("_Test Warehouse", company=company)

		create_account(
			account_name="_Test Bank",
			parent_account="Bank Accounts - _TC",
			company="_Test Company",
			account_currency="INR",
			root_type="Asset",
			account_type="Bank",
			is_group=False
		)
		account = create_account(
			account_name="Open Items",
			parent_account="Accounts Receivable - _TC",
			company=company,
			account_currency="INR",
			do_not_save=True
		)
		account.is_open_item = 1
		account.report_type = "Balance Sheet"
		account.save(ignore_permissions=True)

		item = make_item("_Test Item", {"is_stock_item": 1})

		si1 = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=500,
			income_account=account.name,
			do_not_submit=True
		)
		si1.submit()

		si2 = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=300,
			income_account=account.name,
			do_not_submit=True
		)
		si2.submit()

		pe = create_payment_entry(
			party_type="Customer",
			party="_Test Customer",
			paid_amount=800,
			received_amount=800,
			company=company
		)
		pe.submit()

		si_gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": ["in", [si1.name, si2.name]]}, fields=["name", "credit_in_account_currency"])
		pe_gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": pe.name}, fields=["name", "debit_in_account_currency"])

		credit_gls = [{"gl_entry": gle.name, "outstanding_amount": gle.credit_in_account_currency} for gle in si_gl_entries if gle.credit_in_account_currency > 0]
		debit_gls = [{"gl_entry": gle.name, "outstanding_amount": gle.debit_in_account_currency} for gle in pe_gl_entries if gle.debit_in_account_currency > 0]
	
		doc = frappe.get_doc({
			"doctype": "Open Item Reconciliation",
			"title": "Real GL Allocation",
			"account": account.name,
		}).insert()

		def get_allocated_entry(self, pay, inv, allocated_amount):
			return frappe._dict({
				"credit_gl": inv["gl_entry"],
				"debit_gl": pay["gl_entry"],
				"allocated_amount": allocated_amount
			})
		doc.get_allocated_entry = get_allocated_entry.__get__(doc)

		doc.allocate_entries({
			"debit_gl": debit_gls,
			"credit_gl": credit_gls
		})

		allocs = doc.get("allocation")
		assert len(allocs) == 2
		assert sum(row.allocated_amount for row in allocs) == 800

		for row in allocs:
			assert row.debit_gl in [d["gl_entry"] for d in debit_gls]
			assert row.credit_gl in [c["gl_entry"] for c in credit_gls]
			assert row.allocated_amount > 0

		for row in debit_gls + credit_gls:
			assert row["outstanding_amount"] == 0
   
	def test_get_linked_glr_rows_with_real_gl_entries_TC_ACC_333(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_customer,
			create_sales_invoice,
		)
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
		from frappe.utils import nowdate

		company = "_Test Company"
		create_company(company)
		create_customer(name="_Test Customer", currency="INR")
		create_cost_center(cost_center_name="_Test Cost Center", company=company)
		create_warehouse("_Test Warehouse", company=company)

		account = create_account(
			account_name="Open Items",
			parent_account="Accounts Receivable - _TC",
			company=company,
			account_currency="INR",
			do_not_save=True
		)
		account.is_open_item = 1
		account.report_type = "Balance Sheet"
		account.save(ignore_permissions=True)

		item = make_item("_Test Item", {"is_stock_item": 1})

		si = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			item=item.name,
			rate=1000,
			income_account=account.name,
			do_not_submit=True
		)
		si.submit()

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": si.name},
			fields=["name", "debit_in_account_currency", "credit_in_account_currency"]
		)

		debit_gl = next(g for g in gl_entries if g.debit_in_account_currency > 0)
		credit_gl = next(g for g in gl_entries if g.credit_in_account_currency > 0)

		doc = frappe.get_doc({
			"doctype": "Open Item Reconciliation",
			"title": "Test Linked GLR",
			"account": account.name
		}).insert()

		doc.set("allocation", [])
		doc.append("allocation", {
			"credit_gl": credit_gl.name,
			"debit_gl": debit_gl.name,
			"allocated_amount": 1000
		})
		doc.save()

		reconciliation_pairs = [
			(debit_gl.name, credit_gl.name),
			(credit_gl.name, debit_gl.name)
		]

		for parent_gl, linked_gl in reconciliation_pairs:
			frappe.get_doc({
				"doctype": "GL Entry Reconciliation Details",
				"parent": parent_gl,
				"parenttype": "GL Entry",
				"parentfield": "gl_entry_reconciliation_details",
				"gl_entry": linked_gl,
				"amount": 1000,
				"posting_date": nowdate(),
				"glr_ref_id": doc.name
			}).insert()

		reconciled_entries, unwanted_lines = doc.get_linked_glr_rows()

		self.assertEqual(reconciled_entries, [debit_gl.name, credit_gl.name])
		self.assertEqual(len(unwanted_lines), 2)
		assert all(frappe.db.exists("GL Entry Reconciliation Details", name) for name in unwanted_lines)

		result = doc.get_reconciled_entries()
		assert set(result) == {debit_gl.name, credit_gl.name}


def validate_fiscal_year(company):
	from erpnext.accounts.utils import get_fiscal_year

	year = get_fiscal_year(frappe.utils.today())
	if len(year) > 1:
		fiscal_year = frappe.get_doc("Fiscal Year", year[0])
		company_list = {d.company for d in fiscal_year.companies}
		if company not in company_list:
			fiscal_year.append("companies", {"company": company})
			fiscal_year.save()
