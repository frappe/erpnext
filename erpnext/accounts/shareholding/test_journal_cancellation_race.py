# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from threading import Thread

import frappe
from frappe.utils import nowdate

from erpnext.tests.utils import ERPNextTestSuite


class TestJournalCancellationRace(ERPNextTestSuite):
	def test_cancellation_reads_journal_submission_after_its_snapshot(self):
		if frappe.db.db_type != "mariadb":
			self.skipTest("This regression targets MariaDB snapshot isolation.")
		variable = frappe.db.sql("SHOW VARIABLES LIKE 'innodb_snapshot_isolation'")
		if not variable:
			self.skipTest("The database does not expose innodb_snapshot_isolation.")
		original_isolation = variable[0][1]
		self.load_test_records("Company")
		company = "_Test Company"
		cash = frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0})
		journal = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": company,
				"posting_date": nowdate(),
				"accounts": [
					{
						"account": "Legal Expenses - _TC",
						"debit_in_account_currency": 100,
						"cost_center": "Main - _TC",
					},
					{"account": cash, "credit_in_account_currency": 100},
				],
			}
		).insert(set_name="_Test Shareholding Cancellation Race")
		# The second connection must see the draft before it can submit it.
		frappe.db.commit()  # nosemgrep
		errors = []
		site, sites_path = frappe.local.site, frappe.local.sites_path
		try:
			frappe.db.sql("SET SESSION innodb_snapshot_isolation = 0")
			self.assertEqual(frappe.get_doc("Journal Entry", journal.name).docstatus, 0)

			def submit_journal():
				try:
					frappe.init(site=site, sites_path=sites_path)
					frappe.connect()
					frappe.set_user("Administrator")
					frappe.get_doc("Journal Entry", journal.name).submit()
					# Publish the submission to the cancellation connection.
					frappe.db.commit()  # nosemgrep
				except Exception as error:
					errors.append(error)
				finally:
					frappe.destroy()

			worker = Thread(target=submit_journal)
			worker.start()
			worker.join(timeout=20)
			self.assertFalse(worker.is_alive(), "Concurrent journal submission did not finish")
			self.assertEqual(errors, [])
			# The ordinary read still sees the draft in the cancellation connection.
			self.assertEqual(frappe.get_doc("Journal Entry", journal.name).docstatus, 0)
			transaction = frappe.get_doc(
				{"doctype": "Share Transaction", "name": "_Test Journal Race", "journal_entry": journal.name}
			)
			transaction.cancel_accounting_journal_entry()
			self.assertEqual(
				frappe.db.get_value("Journal Entry", journal.name, "docstatus", for_update=True), 2
			)
			self.assertFalse(frappe.db.exists("GL Entry", {"voucher_no": journal.name, "is_cancelled": 0}))
		finally:
			# Roll back the cancellation, then remove the independently committed fixture.
			frappe.db.rollback()
			if frappe.db.exists("Journal Entry", journal.name):
				cleanup = frappe.get_doc("Journal Entry", journal.name, for_update=True)
				if cleanup.docstatus == 1:
					cleanup.cancel()
				frappe.db.delete("GL Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name})
				frappe.db.delete(
					"Payment Ledger Entry", {"voucher_type": "Journal Entry", "voucher_no": journal.name}
				)
				frappe.delete_doc("Journal Entry", journal.name, force=True)
			frappe.db.commit()  # nosemgrep
			frappe.db.sql("SET SESSION innodb_snapshot_isolation = %s", (original_isolation,))
