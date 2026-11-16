import frappe

from erpnext.accounts.utils import sync_auto_reconcile_config


def execute():
	if frappe.get_single_value("Accounts Settings", "auto_reconcile_payments"):
		sync_auto_reconcile_config(
			frappe.get_single_value("Accounts Settings", "auto_reconciliation_job_trigger")
		)
