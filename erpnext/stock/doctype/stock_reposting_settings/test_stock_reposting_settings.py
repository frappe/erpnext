# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import get_recipients
from erpnext.stock.doctype.stock_reposting_settings import stock_reposting_settings as srs
from erpnext.tests.utils import ERPNextTestSuite

TEST_COMPANY = "_Test Company"
TEST_WAREHOUSE = "_Test Warehouse - _TC"


class TestStockRepostingSettings(ERPNextTestSuite):
	def tearDown(self):
		frappe.db.set_single_value("Stock Reposting Settings", "repost_incorrect_valuation_entries", 0)
		super().tearDown()

	def test_auto_repost_disabled_does_nothing(self):
		frappe.db.set_single_value("Stock Reposting Settings", "repost_incorrect_valuation_entries", 0)
		with patch("frappe.enqueue") as enqueue:
			srs.repost_incorrect_valuation_entries()
			enqueue.assert_not_called()

	def test_auto_repost_enabled_enqueues_per_company(self):
		frappe.db.set_single_value("Stock Reposting Settings", "repost_incorrect_valuation_entries", 1)
		with patch("frappe.enqueue") as enqueue:
			srs.repost_incorrect_valuation_entries()
			self.assertTrue(enqueue.called)
			# one job per company
			self.assertEqual(enqueue.call_count, frappe.db.count("Company"))

	def test_reposts_only_current_financial_year_entries(self):
		item = make_item().name
		fy_start_date = get_fiscal_year(today(), company=TEST_COMPANY)[1]

		current_fy_row = {"item_code": item, "warehouse": TEST_WAREHOUSE, "posting_date": today()}
		prior_fy_row = {
			"item_code": item,
			"warehouse": TEST_WAREHOUSE,
			"posting_date": add_days(fy_start_date, -1),
		}

		calls = []
		variance_path = "erpnext.stock.report.stock_ledger_variance.stock_ledger_variance.get_data"
		with (
			patch.object(
				srs, "create_repost_item_valuation", side_effect=lambda i, w, d: calls.append((i, w, str(d)))
			),
			patch(variance_path, return_value=[current_fy_row, prior_fy_row]),
		):
			srs.repost_incorrect_valuation_entries_for_company(TEST_COMPANY)

		# Only the current-FY entry is reposted; the prior-FY one is ignored.
		self.assertEqual(calls, [(item, TEST_WAREHOUSE, str(today()))])

	def test_skips_when_repost_already_pending(self):
		item = make_item().name
		current_fy_row = {"item_code": item, "warehouse": TEST_WAREHOUSE, "posting_date": today()}

		calls = []
		variance_path = "erpnext.stock.report.stock_ledger_variance.stock_ledger_variance.get_data"
		with (
			patch.object(srs, "has_pending_valuation_repost", return_value=True),
			patch.object(
				srs, "create_repost_item_valuation", side_effect=lambda i, w, d: calls.append((i, w, str(d)))
			),
			patch(variance_path, return_value=[current_fy_row]),
		):
			srs.repost_incorrect_valuation_entries_for_company(TEST_COMPANY)

		self.assertEqual(calls, [])

	def test_value_comparison_excludes_je_and_flags_wrong_account(self):
		fy_start = getdate(today())

		rows = [
			# correct stock account, current FY -> reposted
			{"voucher_type": "Purchase Receipt", "voucher_no": "PR-OK", "posting_date": today()},
			# Journal Entry -> never reposted
			{"voucher_type": "Journal Entry", "voucher_no": "JE-1", "posting_date": today()},
			# warehouse account not of type "Stock" -> notify, not reposted
			{"voucher_type": "Purchase Receipt", "voucher_no": "PR-BADACC", "posting_date": today()},
			# warehouse account with an unset account_type -> unknown, repost (not a false alarm)
			{"voucher_type": "Purchase Receipt", "voucher_no": "PR-NOTYPE", "posting_date": today()},
			# prior financial year -> ignored
			{
				"voucher_type": "Purchase Receipt",
				"voucher_no": "PR-OLD",
				"posting_date": add_days(fy_start, -1),
			},
		]
		accounts = {
			"PR-OK": [("WH-A", "Stock A - _TC", "Stock")],
			"PR-BADACC": [("WH-B", "Debtors - _TC", "Receivable")],
			"PR-NOTYPE": [("WH-C", "Unclassified - _TC", None)],
			"PR-OLD": [("WH-A", "Stock A - _TC", "Stock")],
		}

		reposted = {}
		sent = []
		comparison = (
			"erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison"
		)
		with (
			patch("erpnext.is_perpetual_inventory_enabled", return_value=True),
			patch(f"{comparison}.get_data", return_value=rows),
			patch(
				f"{comparison}.create_reposting_entries",
				side_effect=lambda r, c: reposted.update(rows=r, company=c),
			),
			patch.object(
				srs, "get_voucher_warehouse_accounts", side_effect=lambda vno, c: accounts.get(vno, [])
			),
			patch.object(srs, "get_users_with_role", return_value=["sysmgr@test.com"]),
			patch("frappe.sendmail", side_effect=lambda **kw: sent.append(kw)),
		):
			srs._repost_stock_account_value_comparison(TEST_COMPANY, fy_start)

		# Current-FY, non-Journal-Entry vouchers are reposted: the correct-account one and the one whose
		# account_type is unset (unknown is treated as "proceed", not "wrong account").
		self.assertEqual([r["voucher_no"] for r in reposted["rows"]], ["PR-OK", "PR-NOTYPE"])
		# Only the concrete wrong-account voucher triggers a System Manager notification.
		self.assertEqual(len(sent), 1)
		self.assertIn("PR-BADACC", sent[0]["message"])
		self.assertNotIn("PR-NOTYPE", sent[0]["message"])


class TestStockRepostingSettingsNotification(ERPNextTestSuite):
	def test_notify_reposting_error_to_role(self):
		role = "Notify Reposting Role"

		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

		user = "notify_reposting_error@test.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Test",
					"language": "en",
					"time_zone": "Asia/Kolkata",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)

		frappe.db.set_single_value("Stock Reposting Settings", "notify_reposting_error_to_role", "")

		users = get_recipients()
		self.assertNotIn(user, users)

		frappe.db.set_single_value("Stock Reposting Settings", "notify_reposting_error_to_role", role)

		users = get_recipients()
		self.assertIn(user, users)
