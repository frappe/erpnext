import frappe

from erpnext.accounts.utils import sync_auto_reconcile_config


def execute():
	"""
	Set default Cron Interval and Queue size
	"""
	frappe.db.set_single_value("Accounts Settings", "auto_reconciliation_job_trigger", 15)
	frappe.db.set_single_value("Accounts Settings", "reconciliation_queue_size", 5)

	# Create Scheduler Event record if it doesn't exist
	if frappe.reload_doc("core", "doctype", "scheduler_event", force=True):
		method = "erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
		if not frappe.db.get_all(
			"Scheduler Event", {"scheduled_against": "Process Payment Reconciliation", "method": method}
		):
			frappe.get_doc(
				{
					"doctype": "Scheduler Event",
					"scheduled_against": "Process Payment Reconciliation",
					"method": method,
				}
			).save()

		sync_auto_reconcile_config(15)
