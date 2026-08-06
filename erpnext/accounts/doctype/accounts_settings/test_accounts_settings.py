import frappe

from erpnext.accounts.utils import sync_auto_reconcile_config
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsSettings(ERPNextTestSuite):
	def test_stale_days(self):
		cur_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		cur_settings.allow_stale = 0
		cur_settings.stale_days = 0

		self.assertRaises(frappe.ValidationError, cur_settings.save)

		cur_settings.stale_days = -1
		self.assertRaises(frappe.ValidationError, cur_settings.save)

	def test_auto_reconciliation_job_trigger_creates_missing_scheduler_event(self):
		method = (
			"erpnext.accounts.doctype.process_payment_reconciliation."
			"process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
		)
		frappe.db.delete("Scheduled Job Type", {"method": method})
		frappe.db.delete("Scheduler Event", {"method": method})

		cur_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		self.addCleanup(self._restore_trigger, cur_settings.auto_reconciliation_job_trigger)

		cur_settings.auto_reconciliation_job_trigger = 25
		cur_settings.save()

		self.assertTrue(
			frappe.db.exists(
				"Scheduler Event", {"scheduled_against": "Process Payment Reconciliation", "method": method}
			)
		)
		self.assertEqual(
			frappe.db.get_value("Scheduled Job Type", {"method": method}, "cron_format"), "0/25 * * * *"
		)

	@staticmethod
	def _restore_trigger(value):
		frappe.db.set_single_value("Accounts Settings", "auto_reconciliation_job_trigger", value)
		sync_auto_reconcile_config(value)
