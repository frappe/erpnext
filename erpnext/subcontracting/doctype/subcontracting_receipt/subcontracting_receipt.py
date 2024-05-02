# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

import erpnext
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.utils import get_incoming_rate


class SubcontractingReceipt(SubcontractingController):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
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

	def onload(self):
		self.set_onload(
			"backflush_based_on",
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on"),
		)

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
		super().before_validate()
		self.validate_items_qty()
		self.set_items_bom()
		self.set_items_cost_center()
		self.set_items_expense_account()
		self.reset_rate_for_serial_batch_supplied_items()

	def validate(self):
		if (
			frappe.db.get_single_value("Buying Settings", "backflush_raw_materials_of_subcontract_based_on")
			== "BOM"
		) and not self.has_serial_batch_items():
			self.supplied_items = []

		super().validate()
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
		self.validate_available_qty_for_consumption()
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
		self.set_consumed_qty_in_subcontract_order()
		self.set_subcontracting_order_status()
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.update_status()
		self.delete_auto_created_batches()

	@frappe.whitelist()
	def set_missing_values(self):
		self.calculate_additional_costs()
		self.calculate_supplied_items_qty_and_amount()
		self.calculate_items_qty_and_amount()

	def reset_rate_for_serial_batch_supplied_items(self):
		for item in self.supplied_items:
			if item.serial_no or item.batch_no:
				args = frappe._dict(
					{
						"item_code": item.rm_item_code,
						"warehouse": self.supplier_warehouse,
						"posting_date": self.posting_date,
						"posting_time": self.posting_time,
						"qty": flt(item.consumed_qty),
						"serial_no": item.serial_no,
						"batch_no": item.batch_no,
						"voucher_type": self.doctype,
						"voucher_no": self.name,
						"company": self.company,
						"allow_zero_valuation": 1,
					}
				)
				item.rate = get_incoming_rate(args)

	def has_serial_batch_items(self):
		if not self.get("supplied_items"):
			return False

		for row in self.get("supplied_items"):
			if row.serial_no or row.batch_no:
				return True

	def set_available_qty_for_consumption(self):
		supplied_items_details = {}

		sco_supplied_item = frappe.qb.DocType("Subcontracting Order Supplied Item")
		for item in self.get("items"):
			supplied_items = (
				frappe.qb.from_(sco_supplied_item)
				.select(
					sco_supplied_item.rm_item_code,
					sco_supplied_item.reference_name,
					(sco_supplied_item.total_supplied_qty - sco_supplied_item.consumed_qty).as_(
						"available_qty"
					),
				)
				.where(
					(sco_supplied_item.parent == item.subcontracting_order)
					& (sco_supplied_item.main_item_code == item.item_code)
					& (sco_supplied_item.reference_name == item.subcontracting_order_item)
				)
			).run(as_dict=True)

			if supplied_items:
				supplied_items_details[item.name] = {}

				for supplied_item in supplied_items:
					supplied_items_details[item.name][
						supplied_item.rm_item_code
					] = supplied_item.available_qty
		else:
			for item in self.get("supplied_items"):
				item.available_qty_for_consumption = supplied_items_details.get(item.reference_name, {}).get(
					item.rm_item_code, 0
				)

	def calculate_supplied_items_qty_and_amount(self):
		for item in self.get("supplied_items") or []:
			item.amount = item.rate * item.consumed_qty

		self.set_available_qty_for_consumption()

	def calculate_items_qty_and_amount(self):
		rm_supp_cost = {}
		for item in self.get("supplied_items") or []:
			if item.reference_name in rm_supp_cost:
				rm_supp_cost[item.reference_name] += item.amount
			else:
				rm_supp_cost[item.reference_name] = item.amount

		total_qty = total_amount = 0
		for item in self.items:
			if item.qty and item.name in rm_supp_cost:
				item.rm_supp_cost = rm_supp_cost[item.name]
				item.rm_cost_per_qty = item.rm_supp_cost / item.qty
				rm_supp_cost.pop(item.name)

			item.rate = (
				flt(item.rm_cost_per_qty) + flt(item.service_cost_per_qty) + flt(item.additional_cost_per_qty)
			)

			item.received_qty = item.qty + flt(item.rejected_qty)
			item.amount = item.qty * item.rate
			total_qty += item.qty
			total_amount += item.amount
		else:
			self.total_qty = total_qty
			self.total = total_amount

	def validate_rejected_warehouse(self):
		for item in self.items:
			if flt(item.rejected_qty) and not item.rejected_warehouse:
				if self.rejected_warehouse:
					item.rejected_warehouse = self.rejected_warehouse

				if not item.rejected_warehouse:
					frappe.throw(
						_("Row #{0}: Rejected Warehouse is mandatory for the rejected Item {1}").format(
							item.idx, item.item_code
						)
					)

			if item.get("rejected_warehouse") and (item.get("rejected_warehouse") == item.get("warehouse")):
				frappe.throw(
					_("Row #{0}: Accepted Warehouse and Rejected Warehouse cannot be same").format(item.idx)
				)

	def validate_available_qty_for_consumption(self):
		for item in self.get("supplied_items"):
			precision = item.precision("consumed_qty")
			if (
				item.available_qty_for_consumption
				and flt(item.available_qty_for_consumption, precision) - flt(item.consumed_qty, precision) < 0
			):
				msg = f"""Row {item.idx}: Consumed Qty {flt(item.consumed_qty, precision)}
					must be less than or equal to Available Qty For Consumption
					{flt(item.available_qty_for_consumption, precision)}
					in Consumed Items Table."""

				frappe.throw(_(msg))

	def validate_items_qty(self):
		for item in self.items:
			if not (item.qty or item.rejected_qty):
				frappe.throw(
					_("Row {0}: Accepted Qty and Rejected Qty can't be zero at the same time.").format(
						item.idx
					)
				)

	def set_items_bom(self):
		if self.is_return:
			for item in self.items:
				if not item.bom:
					item.bom = frappe.db.get_value(
						"Subcontracting Receipt Item",
						{"name": item.subcontracting_receipt_item, "parent": self.return_against},
						"bom",
					)
		else:
			for item in self.items:
				if not item.bom:
					item.bom = frappe.db.get_value(
						"Subcontracting Order Item",
						{"name": item.subcontracting_order_item, "parent": item.subcontracting_order},
						"bom",
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
		if not status:
			if self.docstatus == 0:
				status = "Draft"
			elif self.docstatus == 1:
				status = "Completed"

				if self.is_return:
					status = "Return"
				elif self.per_returned == 100:
					status = "Return Issued"

			elif self.docstatus == 2:
				status = "Cancelled"

			if self.is_return:
				frappe.get_doc("Subcontracting Receipt", self.return_against).update_status(
					update_modified=update_modified
				)

		if status:
			frappe.db.set_value(
				"Subcontracting Receipt", self.name, "status", status, update_modified=update_modified
			)

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import process_gl_map

		if not erpnext.is_perpetual_inventory_enabled(self.company):
			return []

		gl_entries = []
		self.make_item_gl_entries(gl_entries, warehouse_account)

		return process_gl_map(gl_entries)

	def make_item_gl_entries(self, gl_entries, warehouse_account=None):
		warehouse_with_no_account = []

		for item in self.items:
			if flt(item.rate) and flt(item.qty):
				if warehouse_account.get(item.warehouse):
					stock_value_diff = frappe.db.get_value(
						"Stock Ledger Entry",
						{
							"voucher_type": "Subcontracting Receipt",
							"voucher_no": self.name,
							"voucher_detail_no": item.name,
							"warehouse": item.warehouse,
							"is_cancelled": 0,
						},
						"stock_value_difference",
					)

					accepted_warehouse_account = warehouse_account[item.warehouse]["account"]
					supplier_warehouse_account = warehouse_account.get(self.supplier_warehouse, {}).get(
						"account"
					)
					remarks = self.get("remarks") or _("Accounting Entry for Stock")

					# Accepted Warehouse Account (Debit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=accepted_warehouse_account,
						cost_center=item.cost_center,
						debit=stock_value_diff,
						credit=0.0,
						remarks=remarks,
						against_account=item.expense_account,
						account_currency=get_account_currency(accepted_warehouse_account),
						project=item.project,
						item=item,
					)
					# Expense Account (Credit)
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=item.expense_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=stock_value_diff,
						remarks=remarks,
						against_account=accepted_warehouse_account,
						account_currency=get_account_currency(item.expense_account),
						project=item.project,
						item=item,
					)

					if flt(item.rm_supp_cost) and supplier_warehouse_account:
						# Supplier Warehouse Account (Credit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=supplier_warehouse_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=flt(item.rm_supp_cost),
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(supplier_warehouse_account),
							project=item.project,
							item=item,
						)
						# Expense Account (Debit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=flt(item.rm_supp_cost),
							credit=0.0,
							remarks=remarks,
							against_account=supplier_warehouse_account,
							account_currency=get_account_currency(item.expense_account),
							project=item.project,
							item=item,
						)

					# Expense Account (Debit)
					if item.additional_cost_per_qty:
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=self.cost_center or self.get_company_default("cost_center"),
							debit=item.qty * item.additional_cost_per_qty,
							credit=0.0,
							remarks=remarks,
							against_account=None,
							account_currency=get_account_currency(item.expense_account),
						)

					if divisional_loss := flt(item.amount - stock_value_diff, item.precision("amount")):
						loss_account = self.get_company_default(
							"stock_adjustment_account", ignore_validation=True
						)

						# Loss Account (Credit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=loss_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=divisional_loss,
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(loss_account),
							project=item.project,
							item=item,
						)
						# Expense Account (Debit)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=divisional_loss,
							credit=0.0,
							remarks=remarks,
							against_account=loss_account,
							account_currency=get_account_currency(item.expense_account),
							project=item.project,
							item=item,
						)
				elif (
					item.warehouse not in warehouse_with_no_account
					or item.rejected_warehouse not in warehouse_with_no_account
				):
					warehouse_with_no_account.append(item.warehouse)

		for row in self.additional_costs:
			credit_amount = (
				flt(row.base_amount)
				if (row.base_amount or row.account_currency != self.company_currency)
				else flt(row.amount)
			)

			# Additional Cost Expense Account (Credit)
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=row.expense_account,
				cost_center=self.cost_center or self.get_company_default("cost_center"),
				debit=0.0,
				credit=credit_amount,
				remarks=remarks,
				against_account=None,
				account_currency=get_account_currency(row.expense_account),
			)

		if warehouse_with_no_account:
			frappe.msgprint(
				_("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)


@frappe.whitelist()
def make_subcontract_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	return make_return_doc("Subcontracting Receipt", source_name, target_doc)
