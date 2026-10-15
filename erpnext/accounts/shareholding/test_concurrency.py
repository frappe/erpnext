# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from threading import Thread
from unittest.mock import patch

import frappe

from erpnext.accounts.shareholding.test_helpers import ShareholdingTestCase


class TestShareholdingConcurrency(ShareholdingTestCase):
	def test_journal_validation_does_not_wait_for_company_lock(self):
		from erpnext.accounts.shareholding.accounting import validate_equity_journal_entry

		issue = self.create_transaction(
			transaction_type="Issue",
			to_shareholder=self.create_shareholder(),
			from_share_number=1,
			to_share_number=3,
			face_value_per_share=10,
			rate_per_share=15,
		)
		journal = frappe.get_doc("Journal Entry", issue.journal_entry)
		# This committed company is visible to both database connections.
		issue.company = journal.company = "_Test Company"
		frappe.db.get_value("Company", issue.company, "name", for_update=True)
		site, sites_path = frappe.local.site, frappe.local.sites_path
		errors = []
		original_get_doc = frappe.get_doc

		def get_source(*args, **kwargs):
			if args == ("Share Transaction", issue.name):
				return issue
			return original_get_doc(*args, **kwargs)

		def validate_on_second_connection():
			try:
				frappe.init(site=site, sites_path=sites_path)
				frappe.connect()
				frappe.set_user("Administrator")
				frappe.db.multisql(
					{
						"mariadb": "SET SESSION innodb_lock_wait_timeout = 2",
						"postgres": "SET LOCAL lock_timeout = '2s'",
					}
				)
				with patch("frappe.get_doc", side_effect=get_source), patch(
					"erpnext.accounts.shareholding.accounting.validate_snapshot"
				):
					validate_equity_journal_entry(journal)
			except Exception as error:
				errors.append(error)
			finally:
				frappe.destroy()

		worker = Thread(target=validate_on_second_connection)
		worker.start()
		worker.join(timeout=8)
		self.assertFalse(worker.is_alive(), "Journal validation waited on the cancellation company lock")
		self.assertEqual(errors, [])
