# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate

from erpnext.accounts.doctype.accounting_period.accounting_period import (
	ClosedAccountingPeriod,
	OverlapError,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.permission_test_utils import make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountingPeriod(ERPNextTestSuite):
	def setUp(self):
		# test_accounting_period_exempted_role leaves its user logged in
		frappe.set_user("Administrator")

	def test_overlap(self):
		ap1 = create_accounting_period(
			start_date="2018-04-01", end_date="2018-06-30", company="Wind Power LLC"
		)
		ap1.save()

		ap2 = create_accounting_period(
			start_date="2018-06-30",
			end_date="2018-07-10",
			company="Wind Power LLC",
			period_name="Test Accounting Period 1",
		)
		self.assertRaises(OverlapError, ap2.save)

	def test_accounting_period(self):
		ap1 = create_accounting_period(period_name="Test Accounting Period 2")
		ap1.save()

		doc = create_sales_invoice(do_not_save=1, cost_center="_Test Company - _TC", warehouse="Stores - _TC")
		self.assertRaises(ClosedAccountingPeriod, doc.save)

	def test_accounting_period_exempted_role(self):
		# Create Accounting Period with exempted role
		ap = create_accounting_period(
			period_name="Test Accounting Period Exempted",
			exempted_role="Accounts Manager",
			start_date="2025-12-01",
			end_date="2025-12-31",
		)
		ap.save()

		# Create users
		users = frappe.get_all("User", filters={"email": ["like", "test%"]}, limit=1)
		user = None

		if users[0].name:
			user = frappe.get_doc("User", users[0].name)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test1@example.com",
					"first_name": "Test1",
				}
			)
			user.insert()

		user.roles = []
		user.append("roles", {"role": "Accounts User"})

		# ---- Non-exempted user should FAIL ----
		user.save(ignore_permissions=True)
		frappe.clear_cache(user=user.name)

		frappe.set_user(user.name)
		posting_date = "2025-12-11"
		doc = create_sales_invoice(
			do_not_save=1,
			posting_date=posting_date,
		)

		with self.assertRaises(frappe.ValidationError):
			doc.submit()

		# ---- Exempted role should PASS ----
		user.append("roles", {"role": "Accounts Manager"})
		user.save(ignore_permissions=True)
		frappe.clear_cache(user=user.name)

		doc = create_sales_invoice(do_not_save=1, posting_date=posting_date)

		doc.submit()  # Should not raise
		self.assertEqual(doc.docstatus, 1)

	def test_insert_without_closed_documents_closes_every_hooked_doctype(self):
		ap = frappe.get_doc(
			{
				"doctype": "Accounting Period",
				"period_name": "Test Accounting Period Bootstrap",
				"company": "_Test Company",
				"start_date": "2018-01-01",
				"end_date": "2018-01-31",
			}
		).insert()

		self.assertEqual(
			sorted(d.document_type for d in ap.closed_documents),
			sorted(frappe.get_hooks("period_closing_doctypes")),
		)
		self.assertTrue(all(d.closed for d in ap.closed_documents))

	def test_only_managers_can_change_a_period(self):
		accounts_user = make_fenced_user("period-accounts-user@example.com", ["Accounts User"])
		accounts_manager = make_fenced_user("period-accounts-manager@example.com", ["Accounts Manager"])

		for ptype in ("create", "write", "delete"):
			self.assertFalse(frappe.has_permission("Accounting Period", ptype, user=accounts_user))
			self.assertTrue(frappe.has_permission("Accounting Period", ptype, user=accounts_manager))
		self.assertTrue(frappe.has_permission("Accounting Period", "read", user=accounts_user))

	def test_cancel_without_gl_inside_closed_period(self):
		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		transfer = make_stock_entry(
			item_code="_Test Item", source="_Test Warehouse - _TC", target="_Test Warehouse 1 - _TC", qty=1
		)
		self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": transfer.name, "is_cancelled": 0}))

		ap = create_accounting_period(period_name="Test Accounting Period Cancel")
		ap.closed_documents[0].document_type = "Stock Entry"
		ap.save()

		self.assertRaisesRegex(ClosedAccountingPeriod, "cannot cancel", transfer.cancel)


def create_accounting_period(**args):
	args = frappe._dict(args)

	accounting_period = frappe.new_doc("Accounting Period")
	accounting_period.start_date = args.start_date or nowdate()
	accounting_period.end_date = args.end_date or nowdate()
	accounting_period.company = args.company or "_Test Company"
	accounting_period.period_name = args.period_name or "_Test_Period_Name_1"
	accounting_period.append("closed_documents", {"document_type": "Sales Invoice", "closed": 1})
	accounting_period.exempted_role = args.exempted_role or ""

	return accounting_period
