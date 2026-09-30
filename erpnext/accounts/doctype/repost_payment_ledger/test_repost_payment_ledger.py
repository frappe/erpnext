# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestRepostPaymentLedger(ERPNextTestSuite):
	"""Repost Payment Ledger auto-selects submitted vouchers on/after a cutoff date
	(unless rows are added manually) and queues them for a ledger rebuild."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_repost(self, **args):
		args = frappe._dict(args)
		doc = frappe.new_doc("Repost Payment Ledger")
		doc.company = COMPANY
		doc.posting_date = args.get("posting_date", "2026-06-01")
		doc.voucher_type = args.get("voucher_type", "Sales Invoice")
		doc.add_manually = args.get("add_manually", 0)
		return doc

	def test_loads_submitted_vouchers_on_or_after_cutoff(self):
		after_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-06-15", rate=100, qty=1)
		on_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-06-01", rate=100, qty=1)
		before_cutoff = create_sales_invoice(company=COMPANY, posting_date="2026-01-15", rate=100, qty=1)

		doc = self.make_repost(posting_date="2026-06-01", voucher_type="Sales Invoice")
		doc.save()  # before_validate loads the vouchers and sets status

		loaded = {v.voucher_no for v in doc.repost_vouchers}
		self.assertIn(after_cutoff.name, loaded)
		# the filter is >= so an invoice posted exactly on the cutoff is included
		self.assertIn(on_cutoff.name, loaded)
		self.assertNotIn(before_cutoff.name, loaded)
		self.assertEqual(doc.repost_status, "Queued")

	def test_add_manually_preserves_user_rows(self):
		# manually add a BEFORE-cutoff invoice (which the filter would never load) while a
		# matching after-cutoff invoice also exists. If auto-loading wrongly ran it would
		# drop the manual row and pull the after-cutoff one, so this distinguishes the modes.
		manual_si = create_sales_invoice(company=COMPANY, posting_date="2026-01-15", rate=100, qty=1)
		create_sales_invoice(company=COMPANY, posting_date="2026-06-15", rate=100, qty=1)

		doc = self.make_repost(add_manually=1, posting_date="2026-06-01")
		doc.append("repost_vouchers", {"voucher_type": "Sales Invoice", "voucher_no": manual_si.name})
		doc.save()

		rows = [(v.voucher_type, v.voucher_no) for v in doc.repost_vouchers]
		self.assertEqual(rows, [("Sales Invoice", manual_si.name)])
