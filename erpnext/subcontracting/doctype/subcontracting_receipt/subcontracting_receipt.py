# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from erpnext.controllers.subcontracting_controller import SubcontractingController


class SubcontractingReceipt(SubcontractingController):
	def __init__(self, *args, **kwargs):
		super(SubcontractingReceipt, self).__init__(*args, **kwargs)
		self.status_updater = [
			{
				"target_dt": "Subcontracting Order Item",
				"join_field": "subcontracting_order_item",
				"target_field": "received_qty",
				"target_parent_dt": "Subcontracting Order",
				"target_parent_field": "per_received",
				"target_ref_field": "qty",
				"source_dt": "Subcontracting Receipt Item",
				"source_field": "received_qty",
				"percent_join_field": "subcontracting_order",
				"overflow_type": "receipt",
			},
		]

	def update_status_updater_args(self):
		if cint(self.is_return):
			self.status_updater.extend(
				[
					{
						"source_dt": "Subcontracting Receipt Item",
						"target_dt": "Subcontracting Order Item",
						"join_field": "subcontracting_order_item",
						"target_field": "returned_qty",
						"source_field": "-1 * qty",
						"extra_cond": """ and exists (select name from `tabSubcontracting Receipt`
						where name=`tabSubcontracting Receipt Item`.parent and is_return=1)""",
					},
					{
						"source_dt": "Subcontracting Receipt Item",
						"target_dt": "Subcontracting Receipt Item",
						"join_field": "subcontracting_receipt_item",
						"target_field": "returned_qty",
						"target_parent_dt": "Subcontracting Receipt",
						"target_parent_field": "per_returned",
						"target_ref_field": "received_qty",
						"source_field": "-1 * received_qty",
						"percent_join_field_parent": "return_against",
					},
				]
			)

	def before_validate(self):
		super(SubcontractingReceipt, self).before_validate()
		self.set_items_cost_center()
		self.set_items_expense_account()

	def validate(self):
		super(SubcontractingReceipt, self).validate()
		self.set_missing_values()
		self.validate_posting_time()
		self.validate_rejected_warehouse()

		if self._action == "submit":
			self.make_batches("warehouse")

		if getdate(self.posting_date) > getdate(nowdate()):
			frappe.throw(_("Posting Date cannot be future date"))

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		self.reset_default_field_value("rejected_warehouse", "items", "rejected_warehouse")
		self.get_current_stock()

	def on_submit(self):
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.set_subcontracting_order_status()
		self.set_consumed_qty_in_subcontract_order()
		self.update_stock_ledger()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit

		update_serial_nos_after_submit(self, "items")

		self.make_gl_entries()
		self.repost_future_sle_and_gle()
		self.update_status()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")
		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.delete_auto_created_batches()
		self.set_consumed_qty_in_subcontract_order()
		self.set_subcontracting_order_status()
		self.update_status()

	@frappe.whitelist()
	def set_missing_values(self):
		self.set_missing_values_in_supplied_items()
		self.set_missing_values_in_items()

	def set_missing_values_in_supplied_items(self):
		for item in self.get("supplied_items") or []:
			item.amount = item.rate * item.consumed_qty

	def set_missing_values_in_items(self):
		rm_supp_cost = {}
		for item in self.get("supplied_items") or []:
			if item.reference_name in rm_supp_cost:
				rm_supp_cost[item.reference_name] += item.amount
			else:
				rm_supp_cost[item.reference_name] = item.amount

		total_qty = total_amount = 0
		for item in self.items:
			if item.name in rm_supp_cost:
				item.rm_supp_cost = rm_supp_cost[item.name]
				item.rm_cost_per_qty = item.rm_supp_cost / item.qty
				rm_supp_cost.pop(item.name)

			if self.is_new() and item.rm_supp_cost > 0:
				item.rate = (
					item.rm_cost_per_qty + (item.service_cost_per_qty or 0) + item.additional_cost_per_qty
				)

			item.received_qty = item.qty + (item.rejected_qty or 0)
			item.amount = item.qty * item.rate
			total_qty += item.qty
			total_amount += item.amount
		else:
			self.total_qty = total_qty
			self.total = total_amount

	def validate_rejected_warehouse(self):
		if not self.rejected_warehouse:
			for item in self.items:
				if item.rejected_qty:
					frappe.throw(
						_("Rejected Warehouse is mandatory against rejected Item {0}").format(item.item_code)
					)

	def set_items_cost_center(self):
		if self.company:
			cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

			for item in self.items:
				if not item.cost_center:
					item.cost_center = cost_center

	def set_items_expense_account(self):
		if self.company:
			expense_account = self.get_company_default("default_expense_account", ignore_validation=True)

			for item in self.items:
				if not item.expense_account:
					item.expense_account = expense_account

	def update_status(self, status=None, update_modified=False):
		if self.docstatus >= 1 and not status:
			if self.docstatus == 1:
				if self.is_return:
					status = "Return"
					return_against = frappe.get_doc("Subcontracting Receipt", self.return_against)
					return_against.run_method("update_status")
				else:
					if self.per_returned == 100:
						status = "Return Issued"
					elif self.status == "Draft":
						status = "Completed"
			elif self.docstatus == 2:
				status = "Cancelled"

		if status:
			frappe.db.set_value("Subcontracting Receipt", self.name, "status", status, update_modified)


@frappe.whitelist()
def make_subcontract_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, target_doc)
