import unittest

import frappe

from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_posting_date_confirmation
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsSettings(ERPNextTestSuite):
	def test_posting_date_confirmation_uses_current_setting(self):
		for enabled in (0, 1, 0):
			frappe.db.set_single_value("Accounts Settings", "confirm_before_resetting_posting_date", enabled)
			self.assertEqual(get_posting_date_confirmation(), enabled)

	def test_enabling_auto_reconciliation_restores_missing_scheduled_job(self):
		method = (
			"erpnext.accounts.doctype.process_payment_reconciliation."
			"process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
		)
		event_filters = {"scheduled_against": "Process Payment Reconciliation", "method": method}
		frappe.db.delete("Scheduled Job Type", {"method": method})
		frappe.db.delete("Scheduler Event", event_filters)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "auto-reconcile-accounts-manager@example.com",
				"first_name": "Accounts Manager",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts Manager"}],
			}
		).insert(ignore_permissions=True)
		previous_user = frappe.session.user
		try:
			frappe.set_user(user.name)
			settings = frappe.get_doc("Accounts Settings")
			settings.auto_reconcile_payments = 1
			settings.auto_reconciliation_job_trigger = 15
			settings.save()
		finally:
			frappe.set_user(previous_user)

		event = frappe.db.exists("Scheduler Event", event_filters)
		job = frappe.db.get_value(
			"Scheduled Job Type",
			{"method": method},
			["frequency", "cron_format", "scheduler_event", "stopped"],
			as_dict=True,
		)
		self.assertTrue(event)
		self.assertIsNotNone(job)
		self.assertEqual(job.frequency, "Cron")
		self.assertEqual(job.cron_format, "0/15 * * * *")
		self.assertEqual(job.scheduler_event, event)
		self.assertFalse(job.stopped)

	def test_changing_interval_restores_missing_scheduler_event(self):
		method = (
			"erpnext.accounts.doctype.process_payment_reconciliation."
			"process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
		)
		event_filters = {"scheduled_against": "Process Payment Reconciliation", "method": method}
		settings = frappe.get_doc("Accounts Settings")
		settings.auto_reconcile_payments = 1
		settings.save()
		frappe.db.delete("Scheduler Event", event_filters)

		interval = 25 if settings.auto_reconciliation_job_trigger != 25 else 26
		settings.auto_reconciliation_job_trigger = interval
		settings.save()

		event = frappe.db.exists("Scheduler Event", event_filters)
		job = frappe.db.get_value(
			"Scheduled Job Type", {"method": method}, ["cron_format", "scheduler_event"], as_dict=True
		)
		self.assertTrue(event)
		self.assertEqual(job.cron_format, f"0/{interval} * * * *")
		self.assertEqual(job.scheduler_event, event)

	def test_saving_auto_reconciliation_repairs_existing_job_without_duplicates(self):
		method = (
			"erpnext.accounts.doctype.process_payment_reconciliation."
			"process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
		)
		event_filters = {"scheduled_against": "Process Payment Reconciliation", "method": method}
		settings = frappe.get_doc("Accounts Settings")
		settings.auto_reconcile_payments = 1
		settings.auto_reconciliation_job_trigger = 15
		settings.save()

		job = frappe.get_doc("Scheduled Job Type", {"method": method})
		job.cron_format = "0/30 * * * *"
		job.scheduler_event = None
		job.stopped = 1
		job.save(ignore_permissions=True)

		settings.save()
		settings.save()

		job.reload()
		self.assertEqual(job.cron_format, "0/15 * * * *")
		self.assertEqual(job.scheduler_event, frappe.db.exists("Scheduler Event", event_filters))
		self.assertFalse(job.stopped)
		self.assertEqual(frappe.db.count("Scheduler Event", event_filters), 1)
		self.assertEqual(frappe.db.count("Scheduled Job Type", {"method": method}), 1)

	def test_stale_days(self):
		cur_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		cur_settings.allow_stale = 0
		cur_settings.stale_days = 0

		self.assertRaises(frappe.ValidationError, cur_settings.save)

		cur_settings.stale_days = -1
		self.assertRaises(frappe.ValidationError, cur_settings.save)
