# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import start_repost
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestRepostAccountingLedger(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def teadDown(self):
		frappe.db.rollback()

	def test_repost_on_both_ledgers(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
		)

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
		# Ledger has incorrect amount
		self.assertNotEqual(res[0], (si.name, 100, 100))

		ral = frappe.new_doc("Repost Accounting Ledger")
		ral.company = self.company
		ral.append("vouchers", {"voucher_type": si.doctype, "voucher_no": si.name})
		ral.save().submit()

		# background jobs don't run on test cases. Manually triggering repost function.
		start_repost(ral.name)

		res = (
			qb.from_(gl)
			.select(gl.voucher_no, Sum(gl.debit).as_("debit"), Sum(gl.credit).as_("credit"))
			.where((gl.voucher_no == si.name) & (gl.is_cancelled == 0))
			.run()
		)
		# Ledger should reflect correct amount post repost
		self.assertEqual(res[0], (si.name, 100, 100))
