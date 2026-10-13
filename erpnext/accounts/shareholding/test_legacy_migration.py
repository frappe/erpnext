# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import nowdate

from erpnext.patches.v17_0.backfill_legacy_share_transfers import move_range, normalize_ranges


class TestLegacyRangeReplay(UnitTestCase):
	def test_issue_transfer_and_purchase(self):
		ranges = move_range([], 3001, 3500, None, "SH-1")
		ranges = move_range(ranges, 3501, 4000, None, "SH-1")
		self.assertEqual(ranges, [(3001, 4000, "SH-1")])

		ranges = move_range(ranges, 3251, 3750, "SH-1", "SH-2")
		self.assertEqual(
			ranges,
			[(3001, 3250, "SH-1"), (3251, 3750, "SH-2"), (3751, 4000, "SH-1")],
		)

		ranges = move_range(ranges, 3251, 3750, "SH-2", None)
		self.assertEqual(ranges, [(3001, 3250, "SH-1"), (3751, 4000, "SH-1")])

	def test_issue_rejects_existing_numbers(self):
		with self.assertRaisesRegex(ValueError, "already been issued"):
			move_range([(1, 100, "SH-1")], 50, 150, None, "SH-2")

	def test_transfer_requires_complete_ownership(self):
		with self.assertRaisesRegex(ValueError, "complete range"):
			move_range([(1, 50, "SH-1"), (60, 100, "SH-1")], 1, 100, "SH-1", "SH-2")

	def test_staged_balance_rejects_overlap(self):
		with self.assertRaisesRegex(ValueError, "overlapping"):
			normalize_ranges([(1, 50, "SH-1"), (40, 100, "SH-1")])


class TestLegacyBackfill(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from erpnext.patches.v17_0.stage_legacy_share_balances import create_staging_table as balances
		from erpnext.patches.v17_0.stage_legacy_shareholders import create_staging_table as identities

		identities()
		balances()

	def test_backfill_preserves_ranges_without_reposting_accounting_and_is_idempotent(self):
		from erpnext.patches.v17_0.backfill_legacy_share_transfers import run_backfill
		from erpnext.patches.v17_0.migrate_legacy_shareholders_to_folios import execute as migrate_folios

		company = "_Test Company"
		type_name = "_Test Legacy Share Type"
		frappe.get_doc({"doctype": "Share Type", "name": type_name, "title": type_name}).db_insert()
		share_class = frappe.get_doc(
			{
				"doctype": "Share Class",
				"class_name": "Legacy Class",
				"class_code": "TEST-LEGACY-CLASS",
				"category": "Ordinary",
				"has_dividend_rights": 0,
				"legacy_share_type": type_name,
			}
		).insert()
		holders = []
		staging = frappe.qb.DocType("Shareholding Legacy Staging")
		for number in (1, 2):
			holder = frappe.get_doc(
				{
					"doctype": "Shareholder",
					"legal_name": f"Legacy Holder {number}",
					"shareholder_type": "Individual",
					"tax_id_type": "Test Tax ID",
					"tax_id": f"LEGACY-{number}",
					"tax_id_country": "India",
				}
			).insert()
			holders.append(holder.name)
			frappe.qb.into(staging).columns("name", "title", "company", "folio_no", "is_company").insert(
				holder.name, holder.legal_name, company, f"LEGACY-FOL-{number}", 0
			).run()
		for name, action, source, destination, start, end in (
			("_Test Legacy Issue", "Issue", None, holders[0], 1, 10),
			("_Test Legacy Transfer", "Transfer", holders[0], holders[1], 4, 6),
			("_Test Legacy Purchase", "Purchase", holders[0], None, 1, 2),
		):
			frappe.get_doc(
				{
					"doctype": "Share Transfer",
					"name": name,
					"docstatus": 1,
					"company": company,
					"share_type": type_name,
					"transfer_type": action,
					"date": nowdate(),
					"from_shareholder": source,
					"to_shareholder": destination,
					"from_no": start,
					"to_no": end,
					"no_of_shares": end - start + 1,
				}
			).db_insert()
		balances = frappe.qb.DocType("Shareholding Legacy Balance Staging")
		for number, (holder, start, end) in enumerate(
			((holders[0], 3, 3), (holders[0], 7, 10), (holders[1], 4, 6))
		):
			frappe.qb.into(balances).columns(
				"name", "parent", "share_type", "from_no", "to_no", "no_of_shares", "is_company"
			).insert(f"TEST-LEGACY-BAL-{number}", holder, type_name, start, end, end - start + 1, 0).run()
		journal_count = frappe.db.count("Journal Entry", {"company": company})
		with patch.dict(frappe.flags, {"in_patch": True}):
			migrate_folios()
			run_backfill()
			run_backfill()
		self.assertEqual(frappe.db.count("Share Ledger Entry", {"share_class": share_class.name}), 4)
		self.assertEqual(frappe.db.count("Journal Entry", {"company": company}), journal_count)
		self.assertEqual(frappe.get_doc("Shareholder", holders[0]).current_holdings[0].quantity, 5)
		self.assertEqual(frappe.get_doc("Shareholder", holders[1]).current_holdings[0].quantity, 3)
		transfer = frappe.get_doc(
			{
				"doctype": "Share Transaction",
				"transaction_type": "Transfer",
				"company": company,
				"share_class": share_class.name,
				"posting_date": nowdate(),
				"from_shareholder": holders[0],
				"to_shareholder": holders[1],
				"from_share_number": 7,
				"to_share_number": 9,
			}
		).insert()
		transfer.submit()
		self.assertEqual(frappe.get_doc("Shareholder", holders[0]).current_holdings[0].quantity, 2)
		self.assertEqual(frappe.get_doc("Shareholder", holders[1]).current_holdings[0].quantity, 6)
		self.assertFalse(transfer.journal_entry)
