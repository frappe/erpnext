# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import get_gl_entries, make_purchase_receipt


class TestRepostAccountingLedger(AccountsTestMixin, IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.enterClassContext(cls.change_settings("Selling Settings", validate_selling_price=0))

	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		update_repost_settings()

	def tearDown(self):
		frappe.db.rollback()

	def test_01_basic_functions(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
		)

		preq = frappe.get_doc(
			make_payment_request(
				dt=si.doctype,
				dn=si.name,
				payment_request_type="Inward",
				party_type="Customer",
				party=si.customer,
			)
		)
		preq.save().submit()

		# Test Validation Error
		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.delete_cancelled_entries = True
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		ral.append(
			"vouchers", {"voucher_type": preq.doctype, "voucher_no": preq.name}
		)  # this should throw validation error
		self.assertRaises(frappe.ValidationError, ral.save)
		ral.vouchers.pop()
		preq.cancel()
		preq.delete()

		pe = get_payment_entry(si.doctype, si.name)
		pe.save().submit()
		ral.append("vouchers", {"voucher_type": pe.doctype, "voucher_no": pe.name})
		ral.save()

		# manually set an incorrect debit amount in DB
		gle = frappe.db.get_all("GL Entry", filters={"voucher_no": si.name, "account": self.debit_to})
		frappe.db.set_value("GL Entry", gle[0], "debit", 90)

		gl = qb.DocType("GL Entry")
		res = (
			qb.from_(gl)
			.select(gl.voucher_no, Sum(gl.debit).as_("debit"), Sum(gl.credit).as_("credit"))
			.where((gl.voucher_no == si.name) & (gl.is_cancelled == 0))
			.run()
		)

		# Assert incorrect ledger balance
		self.assertNotEqual(res[0], (si.name, 100, 100))

		# Submit repost document
		ral.save().submit()

		res = (
			qb.from_(gl)
			.select(gl.voucher_no, Sum(gl.debit).as_("debit"), Sum(gl.credit).as_("credit"))
			.where((gl.voucher_no == si.name) & (gl.is_cancelled == 0))
			.run()
		)

		# Ledger should reflect correct amount post repost
		self.assertEqual(res[0], (si.name, 100, 100))

	def test_02_deferred_accounting_valiations(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			do_not_submit=True,
		)
		si.items[0].enable_deferred_revenue = True
		si.items[0].deferred_revenue_account = self.deferred_revenue
		si.items[0].service_start_date = nowdate()
		si.items[0].service_end_date = add_days(nowdate(), 90)
		si.save().submit()

		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		self.assertRaises(frappe.ValidationError, ral.save)

	@IntegrationTestCase.change_settings("Accounts Settings", {"delete_linked_ledger_entries": 1})
	def test_04_pcv_validation(self):
		# Clear old GL entries so PCV can be submitted.
		gl = frappe.qb.DocType("GL Entry")
		qb.from_(gl).delete().where(gl.company == self.company).run()

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
		)
		fy = get_fiscal_year(today(), company=self.company)
		pcv = frappe.get_doc(
			{
				"doctype": "Period Closing Voucher",
				"transaction_date": today(),
				"period_start_date": fy[1],
				"period_end_date": today(),
				"company": self.company,
				"fiscal_year": fy[0],
				"cost_center": self.cost_center,
				"closing_account_head": self.retained_earnings,
				"remarks": "test",
			}
		)
		pcv.save().submit()

		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		self.assertRaises(frappe.ValidationError, ral.save)

		pcv.reload()
		pcv.cancel()
		pcv.delete()

	def test_03_deletion_flag_and_preview_function(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
		)

		pe = get_payment_entry(si.doctype, si.name)
		pe.save().submit()

		# with deletion flag set
		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.delete_cancelled_entries = True
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		ral.append("vouchers", {"voucher_type": pe.doctype, "voucher_no": pe.name})
		ral.save().submit()

		self.assertIsNone(frappe.db.exists("GL Entry", {"voucher_no": si.name, "is_cancelled": 1}))
		self.assertIsNone(frappe.db.exists("GL Entry", {"voucher_no": pe.name, "is_cancelled": 1}))

	def test_05_without_deletion_flag(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
		)

		pe = get_payment_entry(si.doctype, si.name)
		pe.save().submit()

		# without deletion flag set
		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.delete_cancelled_entries = False
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		ral.append("vouchers", {"voucher_type": pe.doctype, "voucher_no": pe.name})
		ral.save().submit()

		self.assertIsNotNone(frappe.db.exists("GL Entry", {"voucher_no": si.name, "is_cancelled": 1}))
		self.assertIsNotNone(frappe.db.exists("GL Entry", {"voucher_no": pe.name, "is_cancelled": 1}))

	def test_06_repost_purchase_receipt(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		provisional_account = create_account(
			account_name="Provision Account",
			parent_account="Current Liabilities - _TC",
			company=self.company,
		)

		another_provisional_account = create_account(
			account_name="Another Provision Account",
			parent_account="Current Liabilities - _TC",
			company=self.company,
		)

		company = frappe.get_doc("Company", self.company)
		company.enable_provisional_accounting_for_non_stock_items = 1
		company.default_provisional_account = provisional_account
		company.save()

		test_cc = company.cost_center
		default_expense_account = company.service_expense_account

		item = make_item(properties={"is_stock_item": 0})

		pr = make_purchase_receipt(company=self.company, item_code=item.name, rate=1000.0, qty=1.0)
		pr_gl_entries = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles = [
			{"account": provisional_account, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
			{"account": default_expense_account, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
		]
		self.assertEqual(expected_pr_gles, pr_gl_entries)

		# change the provisional account
		frappe.db.set_value(
			"Purchase Receipt Item",
			pr.items[0].name,
			"provisional_expense_account",
			another_provisional_account,
		)

		repost_doc = frappe.new_doc("Repost Accounting Ledger")
		repost_doc.company = self.company
		repost_doc.delete_cancelled_entries = True
		repost_doc.append("vouchers", {"voucher_type": pr.doctype, "voucher_no": pr.name})
		repost_doc.save().submit()

		pr_gles_after_repost = get_gl_entries(pr.doctype, pr.name, skip_cancelled=True)
		expected_pr_gles_after_repost = [
			{"account": default_expense_account, "debit": 1000.0, "credit": 0.0, "cost_center": test_cc},
			{"account": another_provisional_account, "debit": 0.0, "credit": 1000.0, "cost_center": test_cc},
		]
		self.assertEqual(len(pr_gles_after_repost), len(expected_pr_gles_after_repost))
		self.assertEqual(expected_pr_gles_after_repost, pr_gles_after_repost)

		# teardown
		repost_doc.cancel()
		repost_doc.delete()

		pr.reload()
		pr.cancel()

		company.enable_provisional_accounting_for_non_stock_items = 0
		company.default_provisional_account = None
		company.save()


def update_repost_settings():
	allowed_types = [
		"Sales Invoice",
		"Purchase Invoice",
		"Payment Entry",
		"Journal Entry",
		"Purchase Receipt",
	]
	repost_settings = frappe.get_doc("Repost Accounting Ledger Settings")
	for x in allowed_types:
		repost_settings.append("allowed_types", {"document_type": x, "allowed": True})
		repost_settings.save()
