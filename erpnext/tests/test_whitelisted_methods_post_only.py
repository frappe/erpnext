import importlib

import frappe
from frappe.tests.utils import FrappeTestCase

POST_ONLY_METHODS = (
	"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_bank_transaction",
	"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_journal_entry_bts",
	"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_payment_entry_bts",
	"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.reconcile_vouchers",
	"erpnext.accounts.doctype.bank_transaction.bank_transaction_upload.create_bank_entries",
	"erpnext.accounts.doctype.bisect_accounting_statements.bisect_accounting_statements.BisectAccountingStatements.bisect_left",
	"erpnext.accounts.doctype.bisect_accounting_statements.bisect_accounting_statements.BisectAccountingStatements.bisect_right",
	"erpnext.accounts.doctype.bisect_accounting_statements.bisect_accounting_statements.BisectAccountingStatements.move_up",
	"erpnext.accounts.doctype.cheque_print_template.cheque_print_template.create_or_update_cheque_print_format",
	"erpnext.accounts.doctype.payment_request.payment_request.make_payment_request",
	"erpnext.assets.doctype.location.location.add_node",
	"erpnext.buying.doctype.request_for_quotation.request_for_quotation.create_supplier_quotation",
	"erpnext.controllers.stock_controller.make_quality_inspections",
	"erpnext.crm.doctype.lead.lead.make_lead_from_communication",
	"erpnext.crm.doctype.opportunity.opportunity.set_multiple_status",
	"erpnext.crm.doctype.opportunity.opportunity.make_opportunity_from_communication",
	"erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_institution",
	"erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.add_bank_accounts",
	"erpnext.manufacturing.doctype.work_order.work_order.set_work_order_ops",
	"erpnext.manufacturing.doctype.workstation.workstation.Workstation.start_job",
	"erpnext.manufacturing.doctype.workstation.workstation.Workstation.complete_job",
	"erpnext.projects.doctype.project.project.create_duplicate_project",
	"erpnext.projects.doctype.project.project.set_project_status",
	"erpnext.projects.doctype.task.task.set_multiple_status",
	"erpnext.projects.doctype.task.task.add_node",
	"erpnext.projects.doctype.task.task.add_multiple_tasks",
	"erpnext.quality_management.doctype.quality_procedure.quality_procedure.add_node",
	"erpnext.selling.doctype.customer.customer.Customer.get_customer_group_details",
	"erpnext.selling.doctype.sales_order.sales_order.make_work_orders",
	"erpnext.selling.page.point_of_sale.point_of_sale.create_opening_voucher",
	"erpnext.selling.page.point_of_sale.point_of_sale.set_customer_info",
	"erpnext.setup.doctype.company.company.add_node",
	"erpnext.setup.doctype.department.department.add_node",
	"erpnext.setup.doctype.employee.employee.create_user",
	"erpnext.stock.doctype.batch.batch.split_batch",
	"erpnext.stock.doctype.material_request.material_request.raise_work_orders",
	"erpnext.stock.doctype.warehouse.warehouse.add_node",
	"erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison.create_reposting_entries",
	"erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check.create_reposting_entries",
	"erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_purchase_receipt",
	"erpnext.support.doctype.issue.issue.make_issue_from_communication",
	"erpnext.support.doctype.service_level_agreement.service_level_agreement.reset_service_level_agreement",
	"erpnext.telephony.doctype.call_log.call_log.add_call_summary_and_call_type",
)


class TestWhitelistedMethodsPostOnly(FrappeTestCase):
	def test_state_changing_methods_accept_only_post(self):
		for path in POST_ONLY_METHODS:
			with self.subTest(path=path):
				method = resolve(path)
				self.assertIn(method, frappe.whitelisted)
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func.get(method), ["POST"])


def resolve(path: str):
	"""Resolve a dotted path to a module function or a class method."""
	module_path, _, attribute = path.rpartition(".")
	try:
		return getattr(importlib.import_module(module_path), attribute)
	except ModuleNotFoundError:
		module_path, _, class_name = module_path.rpartition(".")
		return getattr(getattr(importlib.import_module(module_path), class_name), attribute)
