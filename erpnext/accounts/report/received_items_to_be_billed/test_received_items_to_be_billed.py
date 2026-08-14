# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.report.received_items_to_be_billed.received_items_to_be_billed import execute
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_pi_from_pr
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestReceivedItemsToBeBilled(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"posting_date": "2026-06-30",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def get_row(self, data, purchase_receipt):
		matches = [row for row in data if row.get("name") == purchase_receipt]
		return matches[0] if matches else None

	def test_unbilled_receipt_appears_with_pending_amount(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		row = self.get_row(self.run_report(), pr.name)

		self.assertIsNotNone(row, "Unbilled Purchase Receipt should appear in the report")
		self.assertEqual(row.get("supplier"), "_Test Supplier")
		self.assertEqual(row.get("item_code"), "_Test Item")
		self.assertEqual(row.get("amount"), 1000.0)
		self.assertEqual(row.get("billed_amount"), 0.0)
		self.assertEqual(row.get("returned_amount"), 0.0)
		self.assertEqual(row.get("pending_amount"), 1000.0)

	def test_billed_receipt_drops_out_of_report(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		self.assertIsNotNone(self.get_row(self.run_report(), pr.name))

		pi = make_pi_from_pr(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = "2026-06-02"
		pi.submit()

		self.assertIsNone(
			self.get_row(self.run_report(), pr.name),
			"Fully billed Purchase Receipt should no longer appear in the report",
		)

	def test_reference_field_filter_limits_to_single_receipt(self):
		first_pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)
		second_pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=3,
			rate=100,
			supplier="_Test Supplier",
			posting_date="2026-06-01",
		)

		data = self.run_report(purchase_receipt=first_pr.name)

		self.assertIsNotNone(self.get_row(data, first_pr.name))
		self.assertIsNone(self.get_row(data, second_pr.name))

	def test_posting_date_cutoff_excludes_later_receipts(self):
		pr = make_purchase_receipt(
			item_code="_Test Item",
			qty=5,
			rate=200,
			supplier="_Test Supplier",
			posting_date="2026-06-15",
		)

		self.assertIsNone(
			self.get_row(self.run_report(posting_date="2026-06-01"), pr.name),
			"Receipt dated after the cutoff should be excluded",
		)
		self.assertIsNotNone(self.get_row(self.run_report(posting_date="2026-06-30"), pr.name))

	def test_project_user_permission_filters_receipts(self):
		from frappe.permissions import add_user_permission

		test_user = f"non-billed-report-{frappe.generate_hash(length=6)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": test_user,
				"first_name": "Non Billed Report User",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		).insert(ignore_permissions=True)

		allowed_project = frappe.get_doc(
			doctype="Project",
			project_name=f"Allowed Project {frappe.generate_hash(length=6)}",
			company="_Test Company",
			status="Open",
		).insert()
		restricted_project = frappe.get_doc(
			doctype="Project",
			project_name=f"Restricted Project {frappe.generate_hash(length=6)}",
			company="_Test Company",
			status="Open",
		).insert()

		def make_receipt(project):
			purchase_receipt = make_purchase_receipt(
				item_code="_Test Item",
				qty=1,
				rate=100,
				supplier="_Test Supplier",
				posting_date="2026-06-01",
				do_not_submit=True,
			)
			purchase_receipt.project = project
			purchase_receipt.save().submit()
			return purchase_receipt

		allowed_receipt = make_receipt(allowed_project.name)
		restricted_receipt = make_receipt(restricted_project.name)

		frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 0)
		add_user_permission("Project", allowed_project.name, test_user, ignore_permissions=True)

		with self.set_user(test_user):
			self.assertIsNotNone(
				self.get_row(self.run_report(purchase_receipt=allowed_receipt.name), allowed_receipt.name)
			)
			self.assertIsNone(
				self.get_row(
					self.run_report(purchase_receipt=restricted_receipt.name), restricted_receipt.name
				)
			)
