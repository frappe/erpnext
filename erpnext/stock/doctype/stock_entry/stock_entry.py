# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, comma_or, cstr, flt, format_time, formatdate, getdate, nowdate

import erpnext
from erpnext.accounts.general_ledger import process_gl_map
from erpnext.controllers.taxes_and_totals import init_landed_taxes_and_totals
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost, validate_bom_no
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.batch.batch import get_batch_no, get_batch_qty, set_batch_nos
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.serial_no.serial_no import (
	get_serial_nos,
	update_serial_nos_after_submit,
)
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
	OpeningEntryAccountError,
)
from erpnext.stock.get_item_details import (
	get_bin_details,
	get_conversion_factor,
	get_default_cost_center,
	get_reserved_qty_for_so,
)
from erpnext.stock.stock_ledger import NegativeStockError, get_previous_sle, get_valuation_rate
from erpnext.stock.utils import get_bin, get_incoming_rate


class FinishedGoodError(frappe.ValidationError):
	pass


class IncorrectValuationRateError(frappe.ValidationError):
	pass


class DuplicateEntryForWorkOrderError(frappe.ValidationError):
	pass


class OperationsNotCompleteError(frappe.ValidationError):
	pass


class MaxSampleAlreadyRetainedError(frappe.ValidationError):
	pass


from erpnext.controllers.stock_controller import StockController

form_grid_templates = {"items": "templates/form_grid/stock_entry_grid.html"}


class StockEntry(StockController):
	def __init__(self, *args, **kwargs):
		super(StockEntry, self).__init__(*args, **kwargs)
		if self.purchase_order:
			self.subcontract_data = frappe._dict(
				{
					"order_doctype": "Purchase Order",
					"order_field": "purchase_order",
					"rm_detail_field": "po_detail",
					"order_supplied_items_field": "Purchase Order Item Supplied",
				}
			)
		else:
			self.subcontract_data = frappe._dict(
				{
					"order_doctype": "Subcontracting Order",
					"order_field": "subcontracting_order",
					"rm_detail_field": "sco_rm_detail",
					"order_supplied_items_field": "Subcontracting Order Supplied Item",
				}
			)

	def get_feed(self):
		return self.stock_entry_type

	def onload(self):
		for item in self.get("items"):
			item.update(get_bin_details(item.item_code, item.s_warehouse))

	def before_validate(self):
		from erpnext.stock.doctype.putaway_rule.putaway_rule import apply_putaway_rule

		apply_rule = self.apply_putaway_rule and (
			self.purpose in ["Material Transfer", "Material Receipt"]
		)

		if self.get("items") and apply_rule:
			apply_putaway_rule(self.doctype, self.get("items"), self.company, purpose=self.purpose)

	def validate(self):
		self.pro_doc = frappe._dict()
		if self.work_order:
			self.pro_doc = frappe.get_doc("Work Order", self.work_order)

		self.validate_posting_time()
		self.validate_purpose()
		self.validate_item()
		self.validate_customer_provided_item()
		self.validate_qty()
		self.set_transfer_qty()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse()
		self.validate_work_order()
		self.validate_bom()
		self.validate_purchase_order()
		self.validate_subcontracting_order()

		if self.purpose in ("Manufacture", "Repack"):
			self.mark_finished_and_scrap_items()
			self.validate_finished_goods()

		self.validate_with_material_request()
		self.validate_batch()
		self.validate_inspection()
		# self.validate_fg_completed_qty()
		self.validate_difference_account()
		self.set_job_card_data()
		self.set_purpose_for_stock_entry()
		self.clean_serial_nos()
		self.validate_duplicate_serial_no()

		if not self.from_bom:
			self.fg_completed_qty = 0.0

		if self._action == "submit":
			self.make_batches("t_warehouse")
		else:
			set_batch_nos(self, "s_warehouse")

		self.validate_serialized_batch()
		self.set_actual_qty()
		self.calculate_rate_and_amount()
		self.validate_putaway_capacity()

		if not self.get("purpose") == "Manufacture":
			# ignore scrap item wh difference and empty source/target wh
			# in Manufacture Entry
			self.reset_default_field_value("from_warehouse", "items", "s_warehouse")
			self.reset_default_field_value("to_warehouse", "items", "t_warehouse")

	def on_submit(self):
		self.update_stock_ledger()

		update_serial_nos_after_submit(self, "items")
		self.update_work_order()
		self.validate_subcontract_order()
		self.update_subcontract_order_supplied_items()
		self.update_subcontracting_order_status()

		self.make_gl_entries()

		self.repost_future_sle_and_gle()
		self.update_cost_in_project()
		self.validate_reserved_serial_no_consumption()
		self.update_transferred_qty()
		self.update_quality_inspection()

		if self.work_order and self.purpose == "Manufacture":
			self.update_so_in_serial_number()

		if self.purpose == "Material Transfer" and self.add_to_transit:
			self.set_material_request_transfer_status("In Transit")
		if self.purpose == "Material Transfer" and self.outgoing_stock_entry:
			self.set_material_request_transfer_status("Completed")

	def on_cancel(self):
		self.update_subcontract_order_supplied_items()
		self.update_subcontracting_order_status()

		if self.work_order and self.purpose == "Material Consumption for Manufacture":
			self.validate_work_order_status()

		self.update_work_order()
		self.update_stock_ledger()

		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Repost Item Valuation")

		self.make_gl_entries_on_cancel()
		self.repost_future_sle_and_gle()
		self.update_cost_in_project()
		self.update_transferred_qty()
		self.update_quality_inspection()
		self.delete_auto_created_batches()
		self.delete_linked_stock_entry()

		if self.purpose == "Material Transfer" and self.add_to_transit:
			self.set_material_request_transfer_status("Not Started")
		if self.purpose == "Material Transfer" and self.outgoing_stock_entry:
			self.set_material_request_transfer_status("In Transit")

	def set_job_card_data(self):
		if self.job_card and not self.work_order:
			data = frappe.db.get_value(
				"Job Card", self.job_card, ["for_quantity", "work_order", "bom_no"], as_dict=1
			)
			self.fg_completed_qty = data.for_quantity
			self.work_order = data.work_order
			self.from_bom = 1
			self.bom_no = data.bom_no

	def validate_work_order_status(self):
		pro_doc = frappe.get_doc("Work Order", self.work_order)
		if pro_doc.status == "Completed":
			frappe.throw(_("Cannot cancel transaction for Completed Work Order."))

	def validate_purpose(self):
		valid_purposes = [
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Material Consumption for Manufacture",
		]

		if self.purpose not in valid_purposes:
			frappe.throw(_("Purpose must be one of {0}").format(comma_or(valid_purposes)))

		if self.job_card and self.purpose not in ["Material Transfer for Manufacture", "Repack"]:
			frappe.throw(
				_(
					"For job card {0}, you can only make the 'Material Transfer for Manufacture' type stock entry"
				).format(self.job_card)
			)

	def delete_linked_stock_entry(self):
		if self.purpose == "Send to Warehouse":
			for d in frappe.get_all(
				"Stock Entry",
				filters={"docstatus": 0, "outgoing_stock_entry": self.name, "purpose": "Receive at Warehouse"},
			):
				frappe.delete_doc("Stock Entry", d.name)

	def set_transfer_qty(self):
		for item in self.get("items"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx), title=_("Zero quantity"))
			if not flt(item.conversion_factor):
				frappe.throw(_("Row {0}: UOM Conversion Factor is mandatory").format(item.idx))
			item.transfer_qty = flt(
				flt(item.qty) * flt(item.conversion_factor), self.precision("transfer_qty", item)
			)
			if not flt(item.transfer_qty):
				frappe.throw(
					_("Row {0}: Qty in Stock UOM can not be zero.").format(item.idx), title=_("Zero quantity")
				)

	def update_cost_in_project(self):
		if self.work_order and not frappe.db.get_value(
			"Work Order", self.work_order, "update_consumed_material_cost_in_project"
		):
			return

		if self.project:
			amount = frappe.db.sql(
				""" select ifnull(sum(sed.amount), 0)
				from
					`tabStock Entry` se, `tabStock Entry Detail` sed
				where
					se.docstatus = 1 and se.project = %s and sed.parent = se.name
					and (sed.t_warehouse is null or sed.t_warehouse = '')""",
				self.project,
				as_list=1,
			)

			amount = amount[0][0] if amount else 0
			additional_costs = frappe.db.sql(
				""" select ifnull(sum(sed.base_amount), 0)
				from
					`tabStock Entry` se, `tabLanded Cost Taxes and Charges` sed
				where
					se.docstatus = 1 and se.project = %s and sed.parent = se.name
					and se.purpose = 'Manufacture'""",
				self.project,
				as_list=1,
			)

			additional_cost_amt = additional_costs[0][0] if additional_costs else 0

			amount += additional_cost_amt
			frappe.db.set_value("Project", self.project, "total_consumed_material_cost", amount)

	def validate_item(self):
		stock_items = self.get_stock_items()
		serialized_items = self.get_serialized_items()
		for item in self.get("items"):
			if flt(item.qty) and flt(item.qty) < 0:
				frappe.throw(
					_("Row {0}: The item {1}, quantity must be positive number").format(
						item.idx, frappe.bold(item.item_code)
					)
				)

			if item.item_code not in stock_items:
				frappe.throw(_("{0} is not a stock Item").format(item.item_code))

			item_details = self.get_item_details(
				frappe._dict(
					{
						"item_code": item.item_code,
						"company": self.company,
						"project": self.project,
						"uom": item.uom,
						"s_warehouse": item.s_warehouse,
					}
				),
				for_update=True,
			)

			reset_fields = ("stock_uom", "item_name")
			for field in reset_fields:
				item.set(field, item_details.get(field))

			update_fields = ("uom", "description", "expense_account", "cost_center", "conversion_factor")

			for field in update_fields:
				if not item.get(field):
					item.set(field, item_details.get(field))
				if field == "conversion_factor" and item.uom == item_details.get("stock_uom"):
					item.set(field, item_details.get(field))

			if not item.transfer_qty and item.qty:
				item.transfer_qty = flt(
					flt(item.qty) * flt(item.conversion_factor), self.precision("transfer_qty", item)
				)

			if (
				self.purpose in ("Material Transfer", "Material Transfer for Manufacture")
				and not item.serial_no
				and item.item_code in serialized_items
			):
				frappe.throw(
					_("Row #{0}: Please specify Serial No for Item {1}").format(item.idx, item.item_code),
					frappe.MandatoryError,
				)

	def validate_qty(self):
		manufacture_purpose = ["Manufacture", "Material Consumption for Manufacture"]

		if self.purpose in manufacture_purpose and self.work_order:
			if not frappe.get_value("Work Order", self.work_order, "skip_transfer"):
				item_code = []
				for item in self.items:
					if cstr(item.t_warehouse) == "":
						req_items = frappe.get_all(
							"Work Order Item",
							filters={"parent": self.work_order, "item_code": item.item_code},
							fields=["item_code"],
						)

						transferred_materials = frappe.db.sql(
							"""
									select
										sum(qty) as qty
									from `tabStock Entry` se,`tabStock Entry Detail` sed
									where
										se.name = sed.parent and se.docstatus=1 and
										(se.purpose='Material Transfer for Manufacture' or se.purpose='Manufacture')
										and sed.item_code=%s and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
								""",
							(item.item_code, self.work_order),
							as_dict=1,
						)

						stock_qty = flt(item.qty)
						trans_qty = flt(transferred_materials[0].qty)
						if req_items:
							if stock_qty > trans_qty:
								item_code.append(item.item_code)

	def validate_fg_completed_qty(self):
		item_wise_qty = {}
		if self.purpose == "Manufacture" and self.work_order:
			for d in self.items:
				if d.is_finished_item or d.is_process_loss:
					item_wise_qty.setdefault(d.item_code, []).append(d.qty)

		for item_code, qty_list in item_wise_qty.items():
			total = flt(sum(qty_list), frappe.get_precision("Stock Entry Detail", "qty"))
			if self.fg_completed_qty != total:
				frappe.throw(
					_("The finished product {0} quantity {1} and For Quantity {2} cannot be different").format(
						frappe.bold(item_code), frappe.bold(total), frappe.bold(self.fg_completed_qty)
					)
				)

	def validate_difference_account(self):
		if not cint(erpnext.is_perpetual_inventory_enabled(self.company)):
			return

		for d in self.get("items"):
			if not d.expense_account:
				frappe.throw(
					_(
						"Please enter <b>Difference Account</b> or set default <b>Stock Adjustment Account</b> for company {0}"
					).format(frappe.bold(self.company))
				)

			elif (
				self.is_opening == "Yes"
				and frappe.db.get_value("Account", d.expense_account, "report_type") == "Profit and Loss"
			):
				frappe.throw(
					_(
						"Difference Account must be a Asset/Liability type account, since this Stock Entry is an Opening Entry"
					),
					OpeningEntryAccountError,
				)

	def validate_warehouse(self):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = [
			"Material Issue",
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
		]

		target_mandatory = [
			"Material Receipt",
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
		]

		validate_for_manufacture = any([d.bom_no for d in self.get("items")])

		if self.purpose in source_mandatory and self.purpose not in target_mandatory:
			self.to_warehouse = None
			for d in self.get("items"):
				d.t_warehouse = None
		elif self.purpose in target_mandatory and self.purpose not in source_mandatory:
			self.from_warehouse = None
			for d in self.get("items"):
				d.s_warehouse = None

		for d in self.get("items"):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.from_warehouse
				d.t_warehouse = self.to_warehouse

			if self.purpose in source_mandatory and not d.s_warehouse:
				if self.from_warehouse:
					d.s_warehouse = self.from_warehouse
				else:
					frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose in target_mandatory and not d.t_warehouse:
				if self.to_warehouse:
					d.t_warehouse = self.to_warehouse
				else:
					frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose == "Manufacture":
				if validate_for_manufacture:
					if d.is_finished_item or d.is_scrap_item or d.is_process_loss:
						d.s_warehouse = None
						if not d.t_warehouse:
							frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))
					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse) and self.purpose not in [
				"Material Transfer for Manufacture",
				"Material Transfer",
			]:
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

			if not (d.s_warehouse or d.t_warehouse):
				frappe.throw(_("Atleast one warehouse is mandatory"))

	def validate_work_order(self):
		if self.purpose in (
			"Manufacture",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
		):
			# check if work order is entered

			if (
				self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture"
			) and self.work_order:
				if not self.fg_completed_qty:
					frappe.throw(_("For Quantity (Manufactured Qty) is mandatory"))
				self.check_if_operations_completed()
				self.check_duplicate_entry_for_work_order()
		elif self.purpose != "Material Transfer":
			self.work_order = None

	def check_if_operations_completed(self):
		"""Check if Time Sheets are completed against before manufacturing to capture operating costs."""
		prod_order = frappe.get_doc("Work Order", self.work_order)
		allowance_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		for d in prod_order.get("operations"):
			total_completed_qty = flt(self.fg_completed_qty) + flt(prod_order.produced_qty)
			completed_qty = d.completed_qty + (allowance_percentage / 100 * d.completed_qty)
			if total_completed_qty > flt(completed_qty):
				job_card = frappe.db.get_value("Job Card", {"operation_id": d.name}, "name")
				if not job_card:
					frappe.throw(
						_("Work Order {0}: Job Card not found for the operation {1}").format(
							self.work_order, d.operation
						)
					)

				work_order_link = frappe.utils.get_link_to_form("Work Order", self.work_order)
				job_card_link = frappe.utils.get_link_to_form("Job Card", job_card)
				frappe.throw(
					_(
						"Row #{0}: Operation {1} is not completed for {2} qty of finished goods in Work Order {3}. Please update operation status via Job Card {4}."
					).format(
						d.idx,
						frappe.bold(d.operation),
						frappe.bold(total_completed_qty),
						work_order_link,
						job_card_link,
					),
					OperationsNotCompleteError,
				)

	def check_duplicate_entry_for_work_order(self):
		other_ste = [
			t[0]
			for t in frappe.db.get_values(
				"Stock Entry",
				{
					"work_order": self.work_order,
					"purpose": self.purpose,
					"docstatus": ["!=", 2],
					"name": ["!=", self.name],
				},
				"name",
			)
		]

		if other_ste:
			production_item, qty = frappe.db.get_value(
				"Work Order", self.work_order, ["production_item", "qty"]
			)
			args = other_ste + [production_item]
			fg_qty_already_entered = frappe.db.sql(
				"""select sum(transfer_qty)
				from `tabStock Entry Detail`
				where parent in (%s)
					and item_code = %s
					and ifnull(s_warehouse,'')='' """
				% (", ".join(["%s" * len(other_ste)]), "%s"),
				args,
			)[0][0]
			if fg_qty_already_entered and fg_qty_already_entered >= qty:
				frappe.throw(
					_("Stock Entries already created for Work Order {0}: {1}").format(
						self.work_order, ", ".join(other_ste)
					),
					DuplicateEntryForWorkOrderError,
				)

	def set_actual_qty(self):
		from erpnext.stock.stock_ledger import is_negative_stock_allowed

		for d in self.get("items"):
			allow_negative_stock = is_negative_stock_allowed(item_code=d.item_code)
			previous_sle = get_previous_sle(
				{
					"item_code": d.item_code,
					"warehouse": d.s_warehouse or d.t_warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
				}
			)

			# get actual stock at source warehouse
			d.actual_qty = previous_sle.get("qty_after_transaction") or 0

			# validate qty during submit
			if (
				d.docstatus == 1
				and d.s_warehouse
				and not allow_negative_stock
				and flt(d.actual_qty, d.precision("actual_qty"))
				< flt(d.transfer_qty, d.precision("actual_qty"))
			):
				frappe.throw(
					_(
						"Row {0}: Quantity not available for {4} in warehouse {1} at posting time of the entry ({2} {3})"
					).format(
						d.idx,
						frappe.bold(d.s_warehouse),
						formatdate(self.posting_date),
						format_time(self.posting_time),
						frappe.bold(d.item_code),
					)
					+ "<br><br>"
					+ _("Available quantity is {0}, you need {1}").format(
						frappe.bold(flt(d.actual_qty, d.precision("actual_qty"))), frappe.bold(d.transfer_qty)
					),
					NegativeStockError,
					title=_("Insufficient Stock"),
				)

	@frappe.whitelist()
	def get_stock_and_rate(self):
		"""
		Updates rate and availability of all the items.
		Called from Update Rate and Availability button.
		"""
		self.set_work_order_details()
		self.set_transfer_qty()
		self.set_actual_qty()
		self.calculate_rate_and_amount()

	def calculate_rate_and_amount(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
		self.set_basic_rate(reset_outgoing_rate, raise_error_if_no_rate)
		init_landed_taxes_and_totals(self)
		self.distribute_additional_costs()
		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()

	def set_basic_rate(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
		"""
		Set rate for outgoing, scrapped and finished items
		"""
		# Set rate for outgoing items
		outgoing_items_cost = self.set_rate_for_outgoing_items(
			reset_outgoing_rate, raise_error_if_no_rate
		)
		finished_item_qty = sum(
			d.transfer_qty for d in self.items if d.is_finished_item or d.is_process_loss
		)

		# Set basic rate for incoming items
		for d in self.get("items"):
			if d.s_warehouse or d.set_basic_rate_manually:
				continue

			if d.allow_zero_valuation_rate:
				d.basic_rate = 0.0
			elif d.is_finished_item:
				if self.purpose == "Manufacture":
					d.basic_rate = self.get_basic_rate_for_manufactured_item(
						finished_item_qty, outgoing_items_cost
					)
				elif self.purpose == "Repack":
					d.basic_rate = self.get_basic_rate_for_repacked_items(d.transfer_qty, outgoing_items_cost)

			if not d.basic_rate and not d.allow_zero_valuation_rate:
				d.basic_rate = get_valuation_rate(
					d.item_code,
					d.t_warehouse,
					self.doctype,
					self.name,
					d.allow_zero_valuation_rate,
					currency=erpnext.get_company_currency(self.company),
					company=self.company,
					raise_error_if_no_rate=raise_error_if_no_rate,
					batch_no=d.batch_no,
				)

			# do not round off basic rate to avoid precision loss
			d.basic_rate = flt(d.basic_rate)
			if d.is_process_loss:
				d.basic_rate = flt(0.0)
			d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

	def set_rate_for_outgoing_items(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
		outgoing_items_cost = 0.0
		for d in self.get("items"):
			if d.s_warehouse:
				if reset_outgoing_rate:
					args = self.get_args_for_incoming_rate(d)
					rate = get_incoming_rate(args, raise_error_if_no_rate)
					if rate > 0:
						d.basic_rate = rate

				d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))
				if not d.t_warehouse:
					outgoing_items_cost += flt(d.basic_amount)

		return outgoing_items_cost

	def get_args_for_incoming_rate(self, item):
		return frappe._dict(
			{
				"item_code": item.item_code,
				"warehouse": item.s_warehouse or item.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": item.s_warehouse and -1 * flt(item.transfer_qty) or flt(item.transfer_qty),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"company": self.company,
				"allow_zero_valuation": item.allow_zero_valuation_rate,
			}
		)

	def get_basic_rate_for_repacked_items(self, finished_item_qty, outgoing_items_cost):
		finished_items = [d.item_code for d in self.get("items") if d.is_finished_item]
		if len(finished_items) == 1:
			return flt(outgoing_items_cost / finished_item_qty)
		else:
			unique_finished_items = set(finished_items)
			if len(unique_finished_items) == 1:
				total_fg_qty = sum([flt(d.transfer_qty) for d in self.items if d.is_finished_item])
				return flt(outgoing_items_cost / total_fg_qty)

	def get_basic_rate_for_manufactured_item(self, finished_item_qty, outgoing_items_cost=0) -> float:
		scrap_items_cost = sum([flt(d.basic_amount) for d in self.get("items") if d.is_scrap_item])

		# Get raw materials cost from BOM if multiple material consumption entries
		if not outgoing_items_cost and frappe.db.get_single_value(
			"Manufacturing Settings", "material_consumption", cache=True
		):
			bom_items = self.get_bom_raw_materials(finished_item_qty)
			outgoing_items_cost = sum([flt(row.qty) * flt(row.rate) for row in bom_items.values()])

		return flt((outgoing_items_cost - scrap_items_cost) / finished_item_qty)

	def distribute_additional_costs(self):
		# If no incoming items, set additional costs blank
		if not any(d.item_code for d in self.items if d.t_warehouse):
			self.additional_costs = []

		self.total_additional_costs = sum(flt(t.base_amount) for t in self.get("additional_costs"))

		if self.purpose in ("Repack", "Manufacture"):
			incoming_items_cost = sum(flt(t.basic_amount) for t in self.get("items") if t.is_finished_item)
		else:
			incoming_items_cost = sum(flt(t.basic_amount) for t in self.get("items") if t.t_warehouse)

		if not incoming_items_cost:
			return

		for d in self.get("items"):
			if self.purpose in ("Repack", "Manufacture") and not d.is_finished_item:
				d.additional_cost = 0
				continue
			elif not d.t_warehouse:
				d.additional_cost = 0
				continue
			d.additional_cost = (flt(d.basic_amount) / incoming_items_cost) * self.total_additional_costs

	def update_valuation_rate(self):
		for d in self.get("items"):
			if d.transfer_qty:
				d.amount = flt(flt(d.basic_amount) + flt(d.additional_cost), d.precision("amount"))
				# Do not round off valuation rate to avoid precision loss
				d.valuation_rate = flt(d.basic_rate) + (flt(d.additional_cost) / flt(d.transfer_qty))

	def set_total_incoming_outgoing_value(self):
		self.total_incoming_value = self.total_outgoing_value = 0.0
		for d in self.get("items"):
			if d.t_warehouse:
				self.total_incoming_value += flt(d.amount)
			if d.s_warehouse:
				self.total_outgoing_value += flt(d.amount)

		self.value_difference = self.total_incoming_value - self.total_outgoing_value

	def set_total_amount(self):
		self.total_amount = None
		if self.purpose not in ["Manufacture", "Repack"]:
			self.total_amount = sum([flt(item.amount) for item in self.get("items")])

	def set_stock_entry_type(self):
		if self.purpose:
			self.stock_entry_type = frappe.get_cached_value(
				"Stock Entry Type", {"purpose": self.purpose}, "name"
			)

	def set_purpose_for_stock_entry(self):
		if self.stock_entry_type and not self.purpose:
			self.purpose = frappe.get_cached_value("Stock Entry Type", self.stock_entry_type, "purpose")

	def validate_duplicate_serial_no(self):
		warehouse_wise_serial_nos = {}

		# In case of repack the source and target serial nos could be same
		for warehouse in ["s_warehouse", "t_warehouse"]:
			serial_nos = []
			for row in self.items:
				if not (row.serial_no and row.get(warehouse)):
					continue

				for sn in get_serial_nos(row.serial_no):
					if sn in serial_nos:
						frappe.throw(
							_("The serial no {0} has added multiple times in the stock entry {1}").format(
								frappe.bold(sn), self.name
							)
						)

					serial_nos.append(sn)

	def validate_subcontract_order(self):
		"""Throw exception if more raw material is transferred against Subcontract Order than in
		the raw materials supplied table"""
		backflush_raw_materials_based_on = frappe.db.get_single_value(
			"Buying Settings", "backflush_raw_materials_of_subcontract_based_on"
		)

		qty_allowance = flt(frappe.db.get_single_value("Buying Settings", "over_transfer_allowance"))

		if not (self.purpose == "Send to Subcontractor" and self.get(self.subcontract_data.order_field)):
			return

		if backflush_raw_materials_based_on == "BOM":
			subcontract_order = frappe.get_doc(
				self.subcontract_data.order_doctype, self.get(self.subcontract_data.order_field)
			)
			for se_item in self.items:
				item_code = se_item.original_item or se_item.item_code
				precision = cint(frappe.db.get_default("float_precision")) or 3
				required_qty = sum(
					[flt(d.required_qty) for d in subcontract_order.supplied_items if d.rm_item_code == item_code]
				)

				total_allowed = required_qty + (required_qty * (qty_allowance / 100))

				if not required_qty:
					bom_no = frappe.db.get_value(
						f"{self.subcontract_data.order_doctype} Item",
						{
							"parent": self.get(self.subcontract_data.order_field),
							"item_code": se_item.subcontracted_item,
						},
						"bom",
					)

					if se_item.allow_alternative_item:
						original_item_code = frappe.get_value(
							"Item Alternative", {"alternative_item_code": item_code}, "item_code"
						)

						required_qty = sum(
							[
								flt(d.required_qty)
								for d in subcontract_order.supplied_items
								if d.rm_item_code == original_item_code
							]
						)

						total_allowed = required_qty + (required_qty * (qty_allowance / 100))

				if not required_qty:
					frappe.throw(
						_("Item {0} not found in 'Raw Materials Supplied' table in {1} {2}").format(
							se_item.item_code,
							self.subcontract_data.order_doctype,
							self.get(self.subcontract_data.order_field),
						)
					)

				se = frappe.qb.DocType("Stock Entry")
				se_detail = frappe.qb.DocType("Stock Entry Detail")

				total_supplied = (
					frappe.qb.from_(se)
					.inner_join(se_detail)
					.on(se.name == se_detail.parent)
					.select(Sum(se_detail.transfer_qty))
					.where(
						(se.purpose == "Send to Subcontractor")
						& (se.docstatus == 1)
						& (se_detail.item_code == se_item.item_code)
						& (
							(se.purchase_order == self.purchase_order)
							if self.subcontract_data.order_doctype == "Purchase Order"
							else (se.subcontracting_order == self.subcontracting_order)
						)
					)
				).run()[0][0]

				if flt(total_supplied, precision) > flt(total_allowed, precision):
					frappe.throw(
						_("Row {0}# Item {1} cannot be transferred more than {2} against {3} {4}").format(
							se_item.idx,
							se_item.item_code,
							total_allowed,
							self.subcontract_data.order_doctype,
							self.get(self.subcontract_data.order_field),
						)
					)
				elif not se_item.get(self.subcontract_data.rm_detail_field):
					filters = {
						"parent": self.get(self.subcontract_data.order_field),
						"docstatus": 1,
						"rm_item_code": se_item.item_code,
						"main_item_code": se_item.subcontracted_item,
					}

					order_rm_detail = frappe.db.get_value(
						self.subcontract_data.order_supplied_items_field, filters, "name"
					)
					if order_rm_detail:
						se_item.db_set(self.subcontract_data.rm_detail_field, order_rm_detail)
					else:
						if not se_item.allow_alternative_item:
							frappe.throw(
								_("Row {0}# Item {1} not found in 'Raw Materials Supplied' table in {2} {3}").format(
									se_item.idx,
									se_item.item_code,
									self.subcontract_data.order_doctype,
									self.get(self.subcontract_data.order_field),
								)
							)
		elif backflush_raw_materials_based_on == "Material Transferred for Subcontract":
			for row in self.items:
				if not row.subcontracted_item:
					frappe.throw(
						_("Row {0}: Subcontracted Item is mandatory for the raw material {1}").format(
							row.idx, frappe.bold(row.item_code)
						)
					)
				elif not row.get(self.subcontract_data.rm_detail_field):
					filters = {
						"parent": self.get(self.subcontract_data.order_field),
						"docstatus": 1,
						"rm_item_code": row.item_code,
						"main_item_code": row.subcontracted_item,
					}

					order_rm_detail = frappe.db.get_value(
						self.subcontract_data.order_supplied_items_field, filters, "name"
					)
					if order_rm_detail:
						row.db_set(self.subcontract_data.rm_detail_field, order_rm_detail)

	def validate_bom(self):
		for d in self.get("items"):
			if d.bom_no and d.is_finished_item:
				item_code = d.original_item or d.item_code
				validate_bom_no(item_code, d.bom_no)

	def validate_purchase_order(self):
		if self.purpose == "Send to Subcontractor" and self.get("purchase_order"):
			is_old_subcontracting_flow = frappe.db.get_value(
				"Purchase Order", self.purchase_order, "is_old_subcontracting_flow"
			)

			if not is_old_subcontracting_flow:
				frappe.throw(
					_("Please select Subcontracting Order instead of Purchase Order {0}").format(
						self.purchase_order
					)
				)

	def validate_subcontracting_order(self):
		if self.get("subcontracting_order") and self.purpose in [
			"Send to Subcontractor",
			"Material Transfer",
		]:
			sco_status = frappe.db.get_value("Subcontracting Order", self.subcontracting_order, "status")

			if sco_status == "Closed":
				frappe.throw(
					_("Cannot create Stock Entry against a closed Subcontracting Order {0}.").format(
						self.subcontracting_order
					)
				)

	def mark_finished_and_scrap_items(self):
		if any([d.item_code for d in self.items if (d.is_finished_item and d.t_warehouse)]):
			return

		finished_item = self.get_finished_item()

		if not finished_item and self.purpose == "Manufacture":
			# In case of independent Manufacture entry, don't auto set
			# user must decide and set
			return

		for d in self.items:
			if d.t_warehouse and not d.s_warehouse:
				if self.purpose == "Repack" or d.item_code == finished_item:
					d.is_finished_item = 1
				else:
					d.is_scrap_item = 1
			else:
				d.is_finished_item = 0
				d.is_scrap_item = 0

	def get_finished_item(self):
		finished_item = None
		if self.work_order:
			finished_item = frappe.db.get_value("Work Order", self.work_order, "production_item")
		elif self.bom_no:
			finished_item = frappe.db.get_value("BOM", self.bom_no, "item")

		return finished_item

	def validate_finished_goods(self):
		"""
		1. Check if FG exists (mfg, repack)
		2. Check if Multiple FG Items are present (mfg)
		3. Check FG Item and Qty against WO if present (mfg)
		"""
		production_item, wo_qty, finished_items = None, 0, []

		wo_details = frappe.db.get_value("Work Order", self.work_order, ["production_item", "qty"])
		if wo_details:
			production_item, wo_qty = wo_details

		for d in self.get("items"):
			if d.is_finished_item:
				if not self.work_order:
					# Independent MFG Entry/ Repack Entry, no WO to match against
					finished_items.append(d.item_code)
					continue

				if d.item_code != production_item:
					frappe.throw(
						_("Finished Item {0} does not match with Work Order {1}").format(
							d.item_code, self.work_order
						)
					)
				elif flt(d.transfer_qty) > flt(self.fg_completed_qty):
					frappe.throw(
						_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}").format(
							d.idx, d.transfer_qty, self.fg_completed_qty
						)
					)

				finished_items.append(d.item_code)

		if not finished_items:
			frappe.throw(
				msg=_("There must be atleast 1 Finished Good in this Stock Entry").format(self.name),
				title=_("Missing Finished Good"),
				exc=FinishedGoodError,
			)

		if self.purpose == "Manufacture":
			if len(set(finished_items)) > 1:
				frappe.throw(
					msg=_("Multiple items cannot be marked as finished item"),
					title=_("Note"),
					exc=FinishedGoodError,
				)

			allowance_percentage = flt(
				frappe.db.get_single_value(
					"Manufacturing Settings", "overproduction_percentage_for_work_order"
				)
			)
			allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

			# No work order could mean independent Manufacture entry, if so skip validation
			if self.work_order and self.fg_completed_qty > allowed_qty:
				frappe.throw(
					_("For quantity {0} should not be greater than allowed quantity {1}").format(
						flt(self.fg_completed_qty), allowed_qty
					)
				)

	def update_stock_ledger(self):
		sl_entries = []
		finished_item_row = self.get_finished_item_row()

		# make sl entries for source warehouse first
		self.get_sle_for_source_warehouse(sl_entries, finished_item_row)

		# SLE for target warehouse
		self.get_sle_for_target_warehouse(sl_entries, finished_item_row)

		# reverse sl entries if cancel
		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries)

	def get_finished_item_row(self):
		finished_item_row = None
		if self.purpose in ("Manufacture", "Repack"):
			for d in self.get("items"):
				if d.is_finished_item:
					finished_item_row = d

		return finished_item_row

	def get_sle_for_source_warehouse(self, sl_entries, finished_item_row):
		for d in self.get("items"):
			if cstr(d.s_warehouse):
				sle = self.get_sl_entries(
					d, {"warehouse": cstr(d.s_warehouse), "actual_qty": -flt(d.transfer_qty), "incoming_rate": 0}
				)
				if cstr(d.t_warehouse):
					sle.dependant_sle_voucher_detail_no = d.name
				elif finished_item_row and (
					finished_item_row.item_code != d.item_code or finished_item_row.t_warehouse != d.s_warehouse
				):
					sle.dependant_sle_voucher_detail_no = finished_item_row.name

				sl_entries.append(sle)

	def get_sle_for_target_warehouse(self, sl_entries, finished_item_row):
		for d in self.get("items"):
			if cstr(d.t_warehouse):
				sle = self.get_sl_entries(
					d,
					{
						"warehouse": cstr(d.t_warehouse),
						"actual_qty": flt(d.transfer_qty),
						"incoming_rate": flt(d.valuation_rate),
					},
				)
				if cstr(d.s_warehouse) or (finished_item_row and d.name == finished_item_row.name):
					sle.recalculate_rate = 1

				sl_entries.append(sle)

	def get_gl_entries(self, warehouse_account):
		gl_entries = super(StockEntry, self).get_gl_entries(warehouse_account)

		if self.purpose in ("Repack", "Manufacture"):
			total_basic_amount = sum(flt(t.basic_amount) for t in self.get("items") if t.is_finished_item)
		else:
			total_basic_amount = sum(flt(t.basic_amount) for t in self.get("items") if t.t_warehouse)

		divide_based_on = total_basic_amount

		if self.get("additional_costs") and not total_basic_amount:
			# if total_basic_amount is 0, distribute additional charges based on qty
			divide_based_on = sum(item.qty for item in list(self.get("items")))

		item_account_wise_additional_cost = {}

		for t in self.get("additional_costs"):
			for d in self.get("items"):
				if self.purpose in ("Repack", "Manufacture") and not d.is_finished_item:
					continue
				elif not d.t_warehouse:
					continue

				item_account_wise_additional_cost.setdefault((d.item_code, d.name), {})
				item_account_wise_additional_cost[(d.item_code, d.name)].setdefault(
					t.expense_account, {"amount": 0.0, "base_amount": 0.0}
				)

				multiply_based_on = d.basic_amount if total_basic_amount else d.qty

				item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account]["amount"] += (
					flt(t.amount * multiply_based_on) / divide_based_on
				)

				item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account]["base_amount"] += (
					flt(t.base_amount * multiply_based_on) / divide_based_on
				)

		if item_account_wise_additional_cost:
			for d in self.get("items"):
				for account, amount in item_account_wise_additional_cost.get(
					(d.item_code, d.name), {}
				).items():
					if not amount:
						continue

					gl_entries.append(
						self.get_gl_dict(
							{
								"account": account,
								"against": d.expense_account,
								"cost_center": d.cost_center,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"credit_in_account_currency": flt(amount["amount"]),
								"credit": flt(amount["base_amount"]),
							},
							item=d,
						)
					)

					gl_entries.append(
						self.get_gl_dict(
							{
								"account": d.expense_account,
								"against": account,
								"cost_center": d.cost_center,
								"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
								"credit": -1
								* amount["base_amount"],  # put it as negative credit instead of debit purposefully
							},
							item=d,
						)
					)

		return process_gl_map(gl_entries)

	def update_work_order(self):
		def _validate_work_order(pro_doc):
			msg, title = "", ""
			if flt(pro_doc.docstatus) != 1:
				msg = f"Work Order {self.work_order} must be submitted"

			if pro_doc.status == "Stopped":
				msg = f"Transaction not allowed against stopped Work Order {self.work_order}"

			if self.is_return and pro_doc.status not in ["Completed", "Closed"]:
				title = _("Stock Return")
				msg = f"Work Order {self.work_order} must be completed or closed"

			if msg:
				frappe.throw(_(msg), title=title)

		if self.job_card:
			job_doc = frappe.get_doc("Job Card", self.job_card)
			job_doc.set_transferred_qty(update_status=True)
			job_doc.set_transferred_qty_in_job_card_item(self)

		if self.work_order:
			pro_doc = frappe.get_doc("Work Order", self.work_order)
			_validate_work_order(pro_doc)
			pro_doc.run_method("update_status")

			if self.fg_completed_qty:
				pro_doc.run_method("update_work_order_qty")
				if self.purpose == "Manufacture":
					pro_doc.run_method("update_planned_qty")
					pro_doc.update_batch_produced_qty(self)

			if not pro_doc.operations:
				pro_doc.set_actual_dates()

	@frappe.whitelist()
	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql(
			"""select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
				i.has_batch_no, i.sample_quantity, i.has_serial_no, i.allow_alternative_item,
				id.expense_account, id.buying_cost_center
			from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
			where i.name=%s
				and i.disabled=0
				and (i.end_of_life is null or i.end_of_life<'1900-01-01' or i.end_of_life > %s)""",
			(self.company, args.get("item_code"), nowdate()),
			as_dict=1,
		)

		if not item:
			frappe.throw(
				_("Item {0} is not active or end of life has been reached").format(args.get("item_code"))
			)

		item = item[0]
		item_group_defaults = get_item_group_defaults(item.name, self.company)
		brand_defaults = get_brand_defaults(item.name, self.company)

		ret = frappe._dict(
			{
				"uom": item.stock_uom,
				"stock_uom": item.stock_uom,
				"description": item.description,
				"image": item.image,
				"item_name": item.item_name,
				"cost_center": get_default_cost_center(
					args, item, item_group_defaults, brand_defaults, self.company
				),
				"qty": args.get("qty"),
				"transfer_qty": args.get("qty"),
				"conversion_factor": 1,
				"batch_no": "",
				"actual_qty": 0,
				"basic_rate": 0,
				"serial_no": "",
				"has_serial_no": item.has_serial_no,
				"has_batch_no": item.has_batch_no,
				"sample_quantity": item.sample_quantity,
				"expense_account": item.expense_account,
			}
		)

		if self.purpose == "Send to Subcontractor":
			ret["allow_alternative_item"] = item.allow_alternative_item

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get("item_code"), args.get("uom"), args.get("qty")))

		if self.purpose == "Material Issue":
			ret["expense_account"] = (
				item.get("expense_account")
				or item_group_defaults.get("expense_account")
				or frappe.get_cached_value("Company", self.company, "default_expense_account")
			)

		for company_field, field in {
			"stock_adjustment_account": "expense_account",
			"cost_center": "cost_center",
		}.items():
			if not ret.get(field):
				ret[field] = frappe.get_cached_value("Company", self.company, company_field)

		args["posting_date"] = self.posting_date
		args["posting_time"] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get("warehouse") else {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		if (
			args.get("s_warehouse", None)
			and args.get("qty")
			and ret.get("has_batch_no")
			and not args.get("batch_no")
		):
			args.batch_no = get_batch_no(args["item_code"], args["s_warehouse"], args["qty"])

		if (
			self.purpose == "Send to Subcontractor"
			and self.get(self.subcontract_data.order_field)
			and args.get("item_code")
		):
			subcontract_items = frappe.get_all(
				self.subcontract_data.order_supplied_items_field,
				{"parent": self.get(self.subcontract_data.order_field), "rm_item_code": args.get("item_code")},
				"main_item_code",
			)

			if subcontract_items and len(subcontract_items) == 1:
				ret["subcontracted_item"] = subcontract_items[0].main_item_code

		return ret

	@frappe.whitelist()
	def set_items_for_stock_in(self):
		self.items = []

		if self.outgoing_stock_entry and self.purpose == "Material Transfer":
			doc = frappe.get_doc("Stock Entry", self.outgoing_stock_entry)

			if doc.per_transferred == 100:
				frappe.throw(_("Goods are already received against the outward entry {0}").format(doc.name))

			for d in doc.items:
				self.append(
					"items",
					{
						"s_warehouse": d.t_warehouse,
						"item_code": d.item_code,
						"qty": d.qty,
						"uom": d.uom,
						"against_stock_entry": d.parent,
						"ste_detail": d.name,
						"stock_uom": d.stock_uom,
						"conversion_factor": d.conversion_factor,
						"serial_no": d.serial_no,
						"batch_no": d.batch_no,
					},
				)

	@frappe.whitelist()
	def get_items(self):
		self.set("items", [])
		self.validate_work_order()

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		self.set_work_order_details()
		self.flags.backflush_based_on = frappe.db.get_single_value(
			"Manufacturing Settings", "backflush_raw_materials_based_on"
		)

		if self.bom_no:

			backflush_based_on = frappe.db.get_single_value(
				"Manufacturing Settings", "backflush_raw_materials_based_on"
			)

			if self.purpose in [
				"Material Issue",
				"Material Transfer",
				"Manufacture",
				"Repack",
				"Send to Subcontractor",
				"Material Transfer for Manufacture",
				"Material Consumption for Manufacture",
			]:

				if self.work_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials(backflush_based_on)
					if self.to_warehouse and self.pro_doc:
						for item in item_dict.values():
							item["to_warehouse"] = self.pro_doc.wip_warehouse
					self.add_to_stock_entry_detail(item_dict)

				elif (
					self.work_order
					and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
					and not self.pro_doc.skip_transfer
					and self.flags.backflush_based_on == "Material Transferred for Manufacture"
				):
					self.add_transfered_raw_materials_in_items()

				elif (
					self.work_order
					and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
					and self.flags.backflush_based_on == "BOM"
					and frappe.db.get_single_value("Manufacturing Settings", "material_consumption") == 1
				):
					self.get_unconsumed_raw_materials()

				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)

					# Get Subcontract Order Supplied Items Details
					if self.get(self.subcontract_data.order_field) and self.purpose == "Send to Subcontractor":
						# Get Subcontract Order Supplied Items Details
						parent = frappe.qb.DocType(self.subcontract_data.order_doctype)
						child = frappe.qb.DocType(self.subcontract_data.order_supplied_items_field)

						item_wh = (
							frappe.qb.from_(parent)
							.inner_join(child)
							.on(parent.name == child.parent)
							.select(child.rm_item_code, child.reserve_warehouse)
							.where(parent.name == self.get(self.subcontract_data.order_field))
						).run(as_list=True)

						item_wh = frappe._dict(item_wh)

					for item in item_dict.values():
						if self.pro_doc and cint(self.pro_doc.from_wip_warehouse):
							item["from_warehouse"] = self.pro_doc.wip_warehouse
						# Get Reserve Warehouse from Subcontract Order
						if self.get(self.subcontract_data.order_field) and self.purpose == "Send to Subcontractor":
							item["from_warehouse"] = item_wh.get(item.item_code)
						item["to_warehouse"] = self.to_warehouse if self.purpose == "Send to Subcontractor" else ""

					self.add_to_stock_entry_detail(item_dict)

			# fetch the serial_no of the first stock entry for the second stock entry
			if self.work_order and self.purpose == "Manufacture":
				work_order = frappe.get_doc("Work Order", self.work_order)
				add_additional_cost(self, work_order)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.load_items_from_bom()

		self.set_scrap_items()
		self.set_actual_qty()
		self.update_items_for_process_loss()
		self.validate_customer_provided_item()
		self.calculate_rate_and_amount(raise_error_if_no_rate=False)

	def set_scrap_items(self):
		if self.purpose != "Send to Subcontractor" and self.purpose in ["Manufacture", "Repack"]:
			scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
			for item in scrap_item_dict.values():
				if self.pro_doc and self.pro_doc.scrap_warehouse:
					item["to_warehouse"] = self.pro_doc.scrap_warehouse

			self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

	def set_work_order_details(self):
		if not getattr(self, "pro_doc", None):
			self.pro_doc = frappe._dict()

		if self.work_order:
			# common validations
			if not self.pro_doc:
				self.pro_doc = frappe.get_doc("Work Order", self.work_order)

			if self.pro_doc:
				self.bom_no = self.pro_doc.bom_no
			else:
				# invalid work order
				self.work_order = None

	def load_items_from_bom(self):
		if self.work_order:
			item_code = self.pro_doc.production_item
			to_warehouse = self.pro_doc.fg_warehouse
		else:
			item_code = frappe.db.get_value("BOM", self.bom_no, "item")
			to_warehouse = self.to_warehouse

		item = get_item_defaults(item_code, self.company)

		if not self.work_order and not to_warehouse:
			# in case of BOM
			to_warehouse = item.get("default_warehouse")

		args = {
			"to_warehouse": to_warehouse,
			"from_warehouse": "",
			"qty": self.fg_completed_qty,
			"item_name": item.item_name,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.get("expense_account"),
			"cost_center": item.get("buying_cost_center"),
			"is_finished_item": 1,
		}

		if (
			self.work_order
			and self.pro_doc.has_batch_no
			and cint(
				frappe.db.get_single_value(
					"Manufacturing Settings", "make_serial_no_batch_from_work_order", cache=True
				)
			)
		):
			self.set_batchwise_finished_goods(args, item)
		else:
			self.add_finished_goods(args, item)

	def set_batchwise_finished_goods(self, args, item):
		filters = {
			"reference_name": self.pro_doc.name,
			"reference_doctype": self.pro_doc.doctype,
			"qty_to_produce": (">", 0),
		}

		fields = ["qty_to_produce as qty", "produced_qty", "name"]

		data = frappe.get_all("Batch", filters=filters, fields=fields, order_by="creation asc")

		if not data:
			self.add_finished_goods(args, item)
		else:
			self.add_batchwise_finished_good(data, args, item)

	def add_batchwise_finished_good(self, data, args, item):
		qty = flt(self.fg_completed_qty)

		for row in data:
			batch_qty = flt(row.qty) - flt(row.produced_qty)
			if not batch_qty:
				continue

			if qty <= 0:
				break

			fg_qty = batch_qty
			if batch_qty >= qty:
				fg_qty = qty

			qty -= batch_qty
			args["qty"] = fg_qty
			args["batch_no"] = row.name

			self.add_finished_goods(args, item)

	def add_finished_goods(self, args, item):
		self.add_to_stock_entry_detail({item.name: args}, bom_no=self.bom_no)

	def get_bom_raw_materials(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(
			self.bom_no,
			self.company,
			qty=qty,
			fetch_exploded=self.use_multi_level_bom,
			fetch_qty_in_stock_uom=False,
		)

		used_alternative_items = get_used_alternative_items(
			subcontract_order_field=self.subcontract_data.order_field, work_order=self.work_order
		)
		for item in item_dict.values():
			# if source warehouse presents in BOM set from_warehouse as bom source_warehouse
			if item["allow_alternative_item"]:
				item["allow_alternative_item"] = frappe.db.get_value(
					"Work Order", self.work_order, "allow_alternative_item"
				)

			item.from_warehouse = self.from_warehouse or item.source_warehouse or item.default_warehouse
			if item.item_code in used_alternative_items:
				alternative_item_data = used_alternative_items.get(item.item_code)
				item.item_code = alternative_item_data.item_code
				item.item_name = alternative_item_data.item_name
				item.stock_uom = alternative_item_data.stock_uom
				item.uom = alternative_item_data.uom
				item.conversion_factor = alternative_item_data.conversion_factor
				item.description = alternative_item_data.description

		return item_dict

	def get_bom_scrap_material(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = (
			get_bom_items_as_dict(self.bom_no, self.company, qty=qty, fetch_exploded=0, fetch_scrap_items=1)
			or {}
		)

		for item in item_dict.values():
			item.from_warehouse = ""
			item.is_scrap_item = 1

		for row in self.get_scrap_items_from_job_card():
			if row.stock_qty <= 0:
				continue

			item_row = item_dict.get(row.item_code)
			if not item_row:
				item_row = frappe._dict({})

			item_row.update(
				{
					"uom": row.stock_uom,
					"from_warehouse": "",
					"qty": row.stock_qty + flt(item_row.stock_qty),
					"converison_factor": 1,
					"is_scrap_item": 1,
					"item_name": row.item_name,
					"description": row.description,
					"allow_zero_valuation_rate": 1,
				}
			)

			item_dict[row.item_code] = item_row

		return item_dict

	def get_scrap_items_from_job_card(self):
		if not self.pro_doc:
			self.set_work_order_details()

		if not self.pro_doc.operations:
			return []

		job_card = frappe.qb.DocType("Job Card")
		job_card_scrap_item = frappe.qb.DocType("Job Card Scrap Item")

		scrap_items = (
			frappe.qb.from_(job_card)
			.select(
				Sum(job_card_scrap_item.stock_qty).as_("stock_qty"),
				job_card_scrap_item.item_code,
				job_card_scrap_item.item_name,
				job_card_scrap_item.description,
				job_card_scrap_item.stock_uom,
			)
			.join(job_card_scrap_item)
			.on(job_card_scrap_item.parent == job_card.name)
			.where(
				(job_card_scrap_item.item_code.isnotnull())
				& (job_card.work_order == self.work_order)
				& (job_card.docstatus == 1)
			)
			.groupby(job_card_scrap_item.item_code)
		).run(as_dict=1)

		pending_qty = flt(self.get_completed_job_card_qty()) - flt(self.pro_doc.produced_qty)

		used_scrap_items = self.get_used_scrap_items()
		for row in scrap_items:
			row.stock_qty -= flt(used_scrap_items.get(row.item_code))
			row.stock_qty = (row.stock_qty) * flt(self.fg_completed_qty) / flt(pending_qty)

			if used_scrap_items.get(row.item_code):
				used_scrap_items[row.item_code] -= row.stock_qty

			if cint(frappe.get_cached_value("UOM", row.stock_uom, "must_be_whole_number")):
				row.stock_qty = frappe.utils.ceil(row.stock_qty)

		return scrap_items

	def get_completed_job_card_qty(self):
		return flt(min([d.completed_qty for d in self.pro_doc.operations]))

	def get_used_scrap_items(self):
		used_scrap_items = defaultdict(float)
		data = frappe.get_all(
			"Stock Entry",
			fields=["`tabStock Entry Detail`.`item_code`", "`tabStock Entry Detail`.`qty`"],
			filters=[
				["Stock Entry", "work_order", "=", self.work_order],
				["Stock Entry Detail", "is_scrap_item", "=", 1],
				["Stock Entry", "docstatus", "=", 1],
				["Stock Entry", "purpose", "in", ["Repack", "Manufacture"]],
			],
		)

		for row in data:
			used_scrap_items[row.item_code] += row.qty

		return used_scrap_items

	def get_unconsumed_raw_materials(self):
		wo = frappe.get_doc("Work Order", self.work_order)
		wo_items = frappe.get_all(
			"Work Order Item",
			filters={"parent": self.work_order},
			fields=["item_code", "source_warehouse", "required_qty", "consumed_qty", "transferred_qty"],
		)

		work_order_qty = wo.material_transferred_for_manufacturing or wo.qty
		for item in wo_items:
			item_account_details = get_item_defaults(item.item_code, self.company)
			# Take into account consumption if there are any.

			wo_item_qty = item.transferred_qty or item.required_qty

			wo_qty_consumed = flt(wo_item_qty) - flt(item.consumed_qty)
			wo_qty_to_produce = flt(work_order_qty) - flt(wo.produced_qty)

			req_qty_each = (wo_qty_consumed) / (wo_qty_to_produce or 1)

			qty = req_qty_each * flt(self.fg_completed_qty)

			if qty > 0:
				self.add_to_stock_entry_detail(
					{
						item.item_code: {
							"from_warehouse": wo.wip_warehouse or item.source_warehouse,
							"to_warehouse": "",
							"qty": qty,
							"item_name": item.item_name,
							"description": item.description,
							"stock_uom": item_account_details.stock_uom,
							"expense_account": item_account_details.get("expense_account"),
							"cost_center": item_account_details.get("buying_cost_center"),
						}
					}
				)

	def add_transfered_raw_materials_in_items(self) -> None:
		available_materials = get_available_materials(self.work_order)

		wo_data = frappe.db.get_value(
			"Work Order",
			self.work_order,
			["qty", "produced_qty", "material_transferred_for_manufacturing as trans_qty"],
			as_dict=1,
		)

		for key, row in available_materials.items():
			remaining_qty_to_produce = flt(wo_data.trans_qty) - flt(wo_data.produced_qty)
			if remaining_qty_to_produce <= 0 and not self.is_return:
				continue

			qty = flt(row.qty)
			if not self.is_return:
				qty = (flt(row.qty) * flt(self.fg_completed_qty)) / remaining_qty_to_produce

			item = row.item_details
			if cint(frappe.get_cached_value("UOM", item.stock_uom, "must_be_whole_number")):
				qty = frappe.utils.ceil(qty)

			if row.batch_details:
				batches = sorted(row.batch_details.items(), key=lambda x: x[0])
				for batch_no, batch_qty in batches:
					if qty <= 0 or batch_qty <= 0:
						continue

					if batch_qty > qty:
						batch_qty = qty

					item.batch_no = batch_no
					self.update_item_in_stock_entry_detail(row, item, batch_qty)

					row.batch_details[batch_no] -= batch_qty
					qty -= batch_qty
			else:
				self.update_item_in_stock_entry_detail(row, item, qty)

	def update_item_in_stock_entry_detail(self, row, item, qty) -> None:
		if not qty:
			return

		ste_item_details = {
			"from_warehouse": item.warehouse,
			"to_warehouse": "",
			"qty": qty,
			"item_name": item.item_name,
			"batch_no": item.batch_no,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.expense_account,
			"cost_center": item.buying_cost_center,
			"original_item": item.original_item,
		}

		if self.is_return:
			ste_item_details["to_warehouse"] = item.s_warehouse

		if row.serial_nos:
			serial_nos = row.serial_nos
			if item.batch_no:
				serial_nos = self.get_serial_nos_based_on_transferred_batch(item.batch_no, row.serial_nos)

			serial_nos = serial_nos[0 : cint(qty)]
			ste_item_details["serial_no"] = "\n".join(serial_nos)

			# remove consumed serial nos from list
			for sn in serial_nos:
				row.serial_nos.remove(sn)

		self.add_to_stock_entry_detail({item.item_code: ste_item_details})

	@staticmethod
	def get_serial_nos_based_on_transferred_batch(batch_no, serial_nos) -> list:
		serial_nos = frappe.get_all(
			"Serial No", filters={"batch_no": batch_no, "name": ("in", serial_nos)}, order_by="creation"
		)

		return [d.name for d in serial_nos]

	def get_pending_raw_materials(self, backflush_based_on=None):
		"""
		issue (item quantity) that is pending to issue or desire to transfer,
		whichever is less
		"""
		item_dict = self.get_pro_order_required_items(backflush_based_on)

		max_qty = flt(self.pro_doc.qty)

		allow_overproduction = False
		overproduction_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		to_transfer_qty = flt(self.pro_doc.material_transferred_for_manufacturing) + flt(
			self.fg_completed_qty
		)
		transfer_limit_qty = max_qty + ((max_qty * overproduction_percentage) / 100)

		if transfer_limit_qty >= to_transfer_qty:
			allow_overproduction = True

		for item, item_details in item_dict.items():
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if (
				desire_to_transfer <= pending_to_issue
				or (desire_to_transfer > 0 and backflush_based_on == "Material Transferred for Manufacture")
				or allow_overproduction
			):
				# "No need for transfer but qty still pending to transfer" case can occur
				# when transferring multiple RM in different Stock Entries
				item_dict[item]["qty"] = desire_to_transfer if (desire_to_transfer > 0) else pending_to_issue
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0

		# delete items with 0 qty
		list_of_items = list(item_dict.keys())
		for item in list_of_items:
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict

	def get_pro_order_required_items(self, backflush_based_on=None):
		"""
		Gets Work Order Required Items only if Stock Entry purpose is **Material Transferred for Manufacture**.
		"""
		item_dict, job_card_items = frappe._dict(), []
		work_order = frappe.get_doc("Work Order", self.work_order)

		consider_job_card = work_order.transfer_material_against == "Job Card" and self.get("job_card")
		if consider_job_card:
			job_card_items = self.get_job_card_item_codes(self.get("job_card"))

		if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
			wip_warehouse = work_order.wip_warehouse
		else:
			wip_warehouse = None

		for d in work_order.get("required_items"):
			if consider_job_card and (d.item_code not in job_card_items):
				continue

			transfer_pending = flt(d.required_qty) > flt(d.transferred_qty)
			can_transfer = transfer_pending or (
				backflush_based_on == "Material Transferred for Manufacture"
			)

			if not can_transfer:
				continue

			if d.include_item_in_manufacturing:
				item_row = d.as_dict()
				item_row["idx"] = len(item_dict) + 1

				if consider_job_card:
					job_card_item = frappe.db.get_value(
						"Job Card Item", {"item_code": d.item_code, "parent": self.get("job_card")}
					)
					item_row["job_card_item"] = job_card_item or None

				if d.source_warehouse and not frappe.db.get_value("Warehouse", d.source_warehouse, "is_group"):
					item_row["from_warehouse"] = d.source_warehouse

				item_row["to_warehouse"] = wip_warehouse
				if item_row["allow_alternative_item"]:
					item_row["allow_alternative_item"] = work_order.allow_alternative_item

				item_dict.setdefault(d.item_code, item_row)

		return item_dict

	def get_job_card_item_codes(self, job_card=None):
		if not job_card:
			return []

		job_card_items = frappe.get_all(
			"Job Card Item", filters={"parent": job_card}, fields=["item_code"], distinct=True
		)
		return [d.item_code for d in job_card_items]

	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		for d in item_dict:
			item_row = item_dict[d]
			stock_uom = item_row.get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

			se_child = self.append("items")
			se_child.s_warehouse = item_row.get("from_warehouse")
			se_child.t_warehouse = item_row.get("to_warehouse")
			se_child.item_code = item_row.get("item_code") or cstr(d)
			se_child.uom = item_row["uom"] if item_row.get("uom") else stock_uom
			se_child.stock_uom = stock_uom
			se_child.qty = flt(item_row["qty"], se_child.precision("qty"))
			se_child.allow_alternative_item = item_row.get("allow_alternative_item", 0)
			se_child.subcontracted_item = item_row.get("main_item_code")
			se_child.cost_center = item_row.get("cost_center") or get_default_cost_center(
				item_row, company=self.company
			)
			se_child.is_finished_item = item_row.get("is_finished_item", 0)
			se_child.is_scrap_item = item_row.get("is_scrap_item", 0)
			se_child.is_process_loss = item_row.get("is_process_loss", 0)
			se_child.po_detail = item_row.get("po_detail")
			se_child.sco_rm_detail = item_row.get("sco_rm_detail")

			for field in [
				self.subcontract_data.rm_detail_field,
				"original_item",
				"expense_account",
				"description",
				"item_name",
				"serial_no",
				"batch_no",
				"allow_zero_valuation_rate",
			]:
				if item_row.get(field):
					se_child.set(field, item_row.get(field))

			if se_child.s_warehouse == None:
				se_child.s_warehouse = self.from_warehouse
			if se_child.t_warehouse == None:
				se_child.t_warehouse = self.to_warehouse

			# in stock uom
			se_child.conversion_factor = flt(item_row.get("conversion_factor")) or 1
			se_child.transfer_qty = flt(
				item_row["qty"] * se_child.conversion_factor, se_child.precision("qty")
			)

			se_child.bom_no = bom_no  # to be assigned for finished item
			se_child.job_card_item = item_row.get("job_card_item") if self.get("job_card") else None

	def validate_with_material_request(self):
		for item in self.get("items"):
			material_request = item.material_request or None
			material_request_item = item.material_request_item or None
			if self.purpose == "Material Transfer" and self.outgoing_stock_entry:
				parent_se = frappe.get_value(
					"Stock Entry Detail",
					item.ste_detail,
					["material_request", "material_request_item"],
					as_dict=True,
				)
				if parent_se:
					material_request = parent_se.material_request
					material_request_item = parent_se.material_request_item

			if material_request:
				mreq_item = frappe.db.get_value(
					"Material Request Item",
					{"name": material_request_item, "parent": material_request},
					["item_code", "warehouse", "idx"],
					as_dict=True,
				)
				if mreq_item.item_code != item.item_code:
					frappe.throw(
						_("Item for row {0} does not match Material Request").format(item.idx),
						frappe.MappingMismatchError,
					)
				elif self.purpose == "Material Transfer" and self.add_to_transit:
					continue

	def validate_batch(self):
		if self.purpose in [
			"Material Transfer for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
		]:
			for item in self.get("items"):
				if item.batch_no:
					disabled = frappe.db.get_value("Batch", item.batch_no, "disabled")
					if disabled == 0:
						expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
						if expiry_date:
							if getdate(self.posting_date) > getdate(expiry_date):
								frappe.throw(_("Batch {0} of Item {1} has expired.").format(item.batch_no, item.item_code))
					else:
						frappe.throw(_("Batch {0} of Item {1} is disabled.").format(item.batch_no, item.item_code))

	def update_subcontract_order_supplied_items(self):
		if self.get(self.subcontract_data.order_field) and (
			self.purpose in ["Send to Subcontractor", "Material Transfer"] or self.is_return
		):

			# Get Subcontract Order Supplied Items Details
			order_supplied_items = frappe.db.get_all(
				self.subcontract_data.order_supplied_items_field,
				filters={"parent": self.get(self.subcontract_data.order_field)},
				fields=["name", "rm_item_code", "reserve_warehouse"],
			)

			# Get Items Supplied in Stock Entries against Subcontract Order
			supplied_items = get_supplied_items(
				self.get(self.subcontract_data.order_field),
				self.subcontract_data.rm_detail_field,
				self.subcontract_data.order_field,
			)

			for row in order_supplied_items:
				key, item = row.name, {}
				if not supplied_items.get(key):
					# no stock transferred against Subcontract Order Supplied Items row
					item = {"supplied_qty": 0, "returned_qty": 0, "total_supplied_qty": 0}
				else:
					item = supplied_items.get(key)

				frappe.db.set_value(self.subcontract_data.order_supplied_items_field, row.name, item)

			# RM Item-Reserve Warehouse Dict
			item_wh = {x.get("rm_item_code"): x.get("reserve_warehouse") for x in order_supplied_items}

			for d in self.get("items"):
				# Update reserved sub contracted quantity in bin based on Supplied Item Details and
				item_code = d.get("original_item") or d.get("item_code")
				reserve_warehouse = item_wh.get(item_code)
				if not (reserve_warehouse and item_code):
					continue
				stock_bin = get_bin(item_code, reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

	def update_so_in_serial_number(self):
		so_name, item_code = frappe.db.get_value(
			"Work Order", self.work_order, ["sales_order", "production_item"]
		)
		if so_name and item_code:
			qty_to_reserve = get_reserved_qty_for_so(so_name, item_code)
			if qty_to_reserve:
				reserved_qty = frappe.db.sql(
					"""select count(name) from `tabSerial No` where item_code=%s and
					sales_order=%s""",
					(item_code, so_name),
				)
				if reserved_qty and reserved_qty[0][0]:
					qty_to_reserve -= reserved_qty[0][0]
				if qty_to_reserve > 0:
					for item in self.items:
						has_serial_no = frappe.get_cached_value("Item", item.item_code, "has_serial_no")
						if item.item_code == item_code and has_serial_no:
							serial_nos = (item.serial_no).split("\n")
							for serial_no in serial_nos:
								if qty_to_reserve > 0:
									frappe.db.set_value("Serial No", serial_no, "sales_order", so_name)
									qty_to_reserve -= 1

	def validate_reserved_serial_no_consumption(self):
		for item in self.items:
			if item.s_warehouse and not item.t_warehouse and item.serial_no:
				for sr in get_serial_nos(item.serial_no):
					sales_order = frappe.db.get_value("Serial No", sr, "sales_order")
					if sales_order:
						msg = _(
							"(Serial No: {0}) cannot be consumed as it's reserverd to fullfill Sales Order {1}."
						).format(sr, sales_order)

						frappe.throw(_("Item {0} {1}").format(item.item_code, msg))

	def update_transferred_qty(self):
		if self.purpose == "Material Transfer" and self.outgoing_stock_entry:
			stock_entries = {}
			stock_entries_child_list = []
			for d in self.items:
				if not (d.against_stock_entry and d.ste_detail):
					continue

				stock_entries_child_list.append(d.ste_detail)
				transferred_qty = frappe.get_all(
					"Stock Entry Detail",
					fields=["sum(qty) as qty"],
					filters={
						"against_stock_entry": d.against_stock_entry,
						"ste_detail": d.ste_detail,
						"docstatus": 1,
					},
				)

				stock_entries[(d.against_stock_entry, d.ste_detail)] = (
					transferred_qty[0].qty if transferred_qty and transferred_qty[0] else 0.0
				) or 0.0

			if not stock_entries:
				return None

			cond = ""
			for data, transferred_qty in stock_entries.items():
				cond += """ WHEN (parent = %s and name = %s) THEN %s
					""" % (
					frappe.db.escape(data[0]),
					frappe.db.escape(data[1]),
					transferred_qty,
				)

			if stock_entries_child_list:
				frappe.db.sql(
					""" UPDATE `tabStock Entry Detail`
					SET
						transferred_qty = CASE {cond} END
					WHERE
						name in ({ste_details}) """.format(
						cond=cond, ste_details=",".join(["%s"] * len(stock_entries_child_list))
					),
					tuple(stock_entries_child_list),
				)

			args = {
				"source_dt": "Stock Entry Detail",
				"target_field": "transferred_qty",
				"target_ref_field": "qty",
				"target_dt": "Stock Entry Detail",
				"join_field": "ste_detail",
				"target_parent_dt": "Stock Entry",
				"target_parent_field": "per_transferred",
				"source_field": "qty",
				"percent_join_field": "against_stock_entry",
			}

			self._update_percent_field_in_targets(args, update_modified=True)

	def update_quality_inspection(self):
		if self.inspection_required:
			reference_type = reference_name = ""
			if self.docstatus == 1:
				reference_name = self.name
				reference_type = "Stock Entry"

			for d in self.items:
				if d.quality_inspection:
					frappe.db.set_value(
						"Quality Inspection",
						d.quality_inspection,
						{"reference_type": reference_type, "reference_name": reference_name},
					)

	def set_material_request_transfer_status(self, status):
		material_requests = []
		if self.outgoing_stock_entry:
			parent_se = frappe.get_value("Stock Entry", self.outgoing_stock_entry, "add_to_transit")

		for item in self.items:
			material_request = item.material_request or None
			if self.purpose == "Material Transfer" and material_request not in material_requests:
				if self.outgoing_stock_entry and parent_se:
					material_request = frappe.get_value("Stock Entry Detail", item.ste_detail, "material_request")

			if material_request and material_request not in material_requests:
				material_requests.append(material_request)
				frappe.db.set_value("Material Request", material_request, "transfer_status", status)

	def update_items_for_process_loss(self):
		process_loss_dict = {}
		for d in self.get("items"):
			if not d.is_process_loss:
				continue

			scrap_warehouse = frappe.db.get_single_value(
				"Manufacturing Settings", "default_scrap_warehouse"
			)
			if scrap_warehouse is not None:
				d.t_warehouse = scrap_warehouse
			d.is_scrap_item = 0

			if d.item_code not in process_loss_dict:
				process_loss_dict[d.item_code] = [flt(0), flt(0)]
			process_loss_dict[d.item_code][0] += flt(d.transfer_qty)
			process_loss_dict[d.item_code][1] += flt(d.qty)

		for d in self.get("items"):
			if not d.is_finished_item or d.item_code not in process_loss_dict:
				continue
			# Assumption: 1 finished item has 1 row.
			d.transfer_qty -= process_loss_dict[d.item_code][0]
			d.qty -= process_loss_dict[d.item_code][1]

	def set_serial_no_batch_for_finished_good(self):
		args = {}
		if self.pro_doc.serial_no:
			self.get_serial_nos_for_fg(args)

		for row in self.items:
			if row.is_finished_item and row.item_code == self.pro_doc.production_item:
				if args.get("serial_no"):
					row.serial_no = "\n".join(args["serial_no"][0 : cint(row.qty)])

	def get_serial_nos_for_fg(self, args):
		fields = [
			"`tabStock Entry`.`name`",
			"`tabStock Entry Detail`.`qty`",
			"`tabStock Entry Detail`.`serial_no`",
			"`tabStock Entry Detail`.`batch_no`",
		]

		filters = [
			["Stock Entry", "work_order", "=", self.work_order],
			["Stock Entry", "purpose", "=", "Manufacture"],
			["Stock Entry", "docstatus", "=", 1],
			["Stock Entry Detail", "item_code", "=", self.pro_doc.production_item],
		]

		stock_entries = frappe.get_all("Stock Entry", fields=fields, filters=filters)

		if self.pro_doc.serial_no:
			args["serial_no"] = self.get_available_serial_nos(stock_entries)

	def get_available_serial_nos(self, stock_entries):
		used_serial_nos = []
		for row in stock_entries:
			if row.serial_no:
				used_serial_nos.extend(get_serial_nos(row.serial_no))

		return sorted(list(set(get_serial_nos(self.pro_doc.serial_no)) - set(used_serial_nos)))

	def update_subcontracting_order_status(self):
		if self.subcontracting_order and self.purpose in ["Send to Subcontractor", "Material Transfer"]:
			from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
				update_subcontracting_order_status,
			)

			update_subcontracting_order_status(self.subcontracting_order)

	def set_missing_values(self):
		"Updates rate and availability of all the items of mapped doc."
		self.set_transfer_qty()
		self.set_actual_qty()
		self.calculate_rate_and_amount()


@frappe.whitelist()
def move_sample_to_retention_warehouse(company, items):
	if isinstance(items, str):
		items = json.loads(items)
	retention_warehouse = frappe.db.get_single_value("Stock Settings", "sample_retention_warehouse")
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.company = company
	stock_entry.purpose = "Material Transfer"
	stock_entry.set_stock_entry_type()
	for item in items:
		if item.get("sample_quantity") and item.get("batch_no"):
			sample_quantity = validate_sample_quantity(
				item.get("item_code"),
				item.get("sample_quantity"),
				item.get("transfer_qty") or item.get("qty"),
				item.get("batch_no"),
			)
			if sample_quantity:
				sample_serial_nos = ""
				if item.get("serial_no"):
					serial_nos = (item.get("serial_no")).split()
					if serial_nos and len(serial_nos) > item.get("sample_quantity"):
						serial_no_list = serial_nos[: -(len(serial_nos) - item.get("sample_quantity"))]
						sample_serial_nos = "\n".join(serial_no_list)

				stock_entry.append(
					"items",
					{
						"item_code": item.get("item_code"),
						"s_warehouse": item.get("t_warehouse"),
						"t_warehouse": retention_warehouse,
						"qty": item.get("sample_quantity"),
						"basic_rate": item.get("valuation_rate"),
						"uom": item.get("uom"),
						"stock_uom": item.get("stock_uom"),
						"conversion_factor": 1.0,
						"serial_no": sample_serial_nos,
						"batch_no": item.get("batch_no"),
					},
				)
	if stock_entry.get("items"):
		return stock_entry.as_dict()


@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.set_stock_entry_type()
		target.set_missing_values()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.t_warehouse = ""

		if source_doc.material_request_item and source_doc.material_request:
			add_to_transit = frappe.db.get_value("Stock Entry", source_name, "add_to_transit")
			if add_to_transit:
				warehouse = frappe.get_value(
					"Material Request Item", source_doc.material_request_item, "warehouse"
				)
				target_doc.t_warehouse = warehouse

		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty - source_doc.transferred_qty

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {"name": "outgoing_stock_entry"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "ste_detail",
					"parent": "against_stock_entry",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
				},
				"postprocess": update_item,
				"condition": lambda doc: flt(doc.qty) - flt(doc.transferred_qty) > 0.01,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def get_work_order_details(work_order, company):
	work_order = frappe.get_doc("Work Order", work_order)
	pending_qty_to_produce = flt(work_order.qty) - flt(work_order.produced_qty)

	return {
		"from_bom": 1,
		"bom_no": work_order.bom_no,
		"use_multi_level_bom": work_order.use_multi_level_bom,
		"wip_warehouse": work_order.wip_warehouse,
		"fg_warehouse": work_order.fg_warehouse,
		"fg_completed_qty": pending_qty_to_produce,
	}


def get_operating_cost_per_unit(work_order=None, bom_no=None):
	operating_cost_per_unit = 0
	if work_order:
		if not bom_no:
			bom_no = work_order.bom_no

		for d in work_order.get("operations"):
			if flt(d.completed_qty):
				operating_cost_per_unit += flt(d.actual_operating_cost) / flt(d.completed_qty)
			elif work_order.qty:
				operating_cost_per_unit += flt(d.planned_operating_cost) / flt(work_order.qty)

	# Get operating cost from BOM if not found in work_order.
	if not operating_cost_per_unit and bom_no:
		bom = frappe.db.get_value("BOM", bom_no, ["operating_cost", "quantity"], as_dict=1)
		if bom.quantity:
			operating_cost_per_unit = flt(bom.operating_cost) / flt(bom.quantity)

	if (
		work_order
		and work_order.produced_qty
		and cint(
			frappe.db.get_single_value(
				"Manufacturing Settings", "add_corrective_operation_cost_in_finished_good_valuation"
			)
		)
	):
		operating_cost_per_unit += flt(work_order.corrective_operation_cost) / flt(
			work_order.produced_qty
		)

	return operating_cost_per_unit


def get_used_alternative_items(
	subcontract_order=None, subcontract_order_field="subcontracting_order", work_order=None
):
	cond = ""

	if subcontract_order:
		cond = f"and ste.purpose = 'Send to Subcontractor' and ste.{subcontract_order_field} = '{subcontract_order}'"
	elif work_order:
		cond = "and ste.purpose = 'Material Transfer for Manufacture' and ste.work_order = '{0}'".format(
			work_order
		)

	if not cond:
		return {}

	used_alternative_items = {}
	data = frappe.db.sql(
		""" select sted.original_item, sted.uom, sted.conversion_factor,
			sted.item_code, sted.item_name, sted.conversion_factor,sted.stock_uom, sted.description
		from
			`tabStock Entry` ste, `tabStock Entry Detail` sted
		where
			sted.parent = ste.name and ste.docstatus = 1 and sted.original_item !=  sted.item_code
			{0} """.format(
			cond
		),
		as_dict=1,
	)

	for d in data:
		used_alternative_items[d.original_item] = d

	return used_alternative_items


def get_valuation_rate_for_finished_good_entry(work_order):
	work_order_qty = flt(
		frappe.get_cached_value("Work Order", work_order, "material_transferred_for_manufacturing")
	)

	field = "(SUM(total_outgoing_value) / %s) as valuation_rate" % (work_order_qty)

	stock_data = frappe.get_all(
		"Stock Entry",
		fields=field,
		filters={
			"docstatus": 1,
			"purpose": "Material Transfer for Manufacture",
			"work_order": work_order,
		},
	)

	if stock_data:
		return stock_data[0].valuation_rate


@frappe.whitelist()
def get_uom_details(item_code, uom, qty):
	"""Returns dict `{"conversion_factor": [value], "transfer_qty": qty * [value]}`
	:param args: dict with `item_code`, `uom` and `qty`"""
	conversion_factor = get_conversion_factor(item_code, uom).get("conversion_factor")

	if not conversion_factor:
		frappe.msgprint(
			_("UOM coversion factor required for UOM: {0} in Item: {1}").format(uom, item_code)
		)
		ret = {"uom": ""}
	else:
		ret = {
			"conversion_factor": flt(conversion_factor),
			"transfer_qty": flt(qty) * flt(conversion_factor),
		}
	return ret


@frappe.whitelist()
def get_expired_batch_items():
	return frappe.db.sql(
		"""select b.item, sum(sle.actual_qty) as qty, sle.batch_no, sle.warehouse, sle.stock_uom\
	from `tabBatch` b, `tabStock Ledger Entry` sle
	where b.expiry_date <= %s
	and b.expiry_date is not NULL
	and b.batch_id = sle.batch_no and sle.is_cancelled = 0
	group by sle.warehouse, sle.item_code, sle.batch_no""",
		(nowdate()),
		as_dict=1,
	)


@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)

	ret = {}
	if args.warehouse and args.item_code:
		args.update(
			{
				"posting_date": args.posting_date,
				"posting_time": args.posting_time,
			}
		)
		ret = {
			"actual_qty": get_previous_sle(args).get("qty_after_transaction") or 0,
			"basic_rate": get_incoming_rate(args),
		}
	return ret


@frappe.whitelist()
def validate_sample_quantity(item_code, sample_quantity, qty, batch_no=None):
	if cint(qty) < cint(sample_quantity):
		frappe.throw(
			_("Sample quantity {0} cannot be more than received quantity {1}").format(sample_quantity, qty)
		)
	retention_warehouse = frappe.db.get_single_value("Stock Settings", "sample_retention_warehouse")
	retainted_qty = 0
	if batch_no:
		retainted_qty = get_batch_qty(batch_no, retention_warehouse, item_code)
	max_retain_qty = frappe.get_value("Item", item_code, "sample_quantity")
	if retainted_qty >= max_retain_qty:
		frappe.msgprint(
			_(
				"Maximum Samples - {0} have already been retained for Batch {1} and Item {2} in Batch {3}."
			).format(retainted_qty, batch_no, item_code, batch_no),
			alert=True,
		)
		sample_quantity = 0
	qty_diff = max_retain_qty - retainted_qty
	if cint(sample_quantity) > cint(qty_diff):
		frappe.msgprint(
			_("Maximum Samples - {0} can be retained for Batch {1} and Item {2}.").format(
				max_retain_qty, batch_no, item_code
			),
			alert=True,
		)
		sample_quantity = qty_diff
	return sample_quantity


def get_supplied_items(
	subcontract_order, rm_detail_field="sco_rm_detail", subcontract_order_field="subcontracting_order"
):
	fields = [
		"`tabStock Entry Detail`.`transfer_qty`",
		"`tabStock Entry`.`is_return`",
		f"`tabStock Entry Detail`.`{rm_detail_field}`",
		"`tabStock Entry Detail`.`item_code`",
	]

	filters = [
		["Stock Entry", "docstatus", "=", 1],
		["Stock Entry", subcontract_order_field, "=", subcontract_order],
	]

	supplied_item_details = {}
	for row in frappe.get_all("Stock Entry", fields=fields, filters=filters):
		if not row.get(rm_detail_field):
			continue

		key = row.get(rm_detail_field)
		if key not in supplied_item_details:
			supplied_item_details.setdefault(
				key, frappe._dict({"supplied_qty": 0, "returned_qty": 0, "total_supplied_qty": 0})
			)

		supplied_item = supplied_item_details[key]

		if row.is_return:
			supplied_item.returned_qty += row.transfer_qty
		else:
			supplied_item.supplied_qty += row.transfer_qty

		supplied_item.total_supplied_qty = flt(supplied_item.supplied_qty) - flt(
			supplied_item.returned_qty
		)

	return supplied_item_details


@frappe.whitelist()
def get_items_from_subcontract_order(source_name, target_doc=None):
	from erpnext.controllers.subcontracting_controller import make_rm_stock_entry

	if isinstance(target_doc, str):
		target_doc = frappe.get_doc(json.loads(target_doc))

	order_doctype = "Purchase Order" if target_doc.purchase_order else "Subcontracting Order"
	target_doc = make_rm_stock_entry(
		subcontract_order=source_name, order_doctype=order_doctype, target_doc=target_doc
	)

	return target_doc


def get_available_materials(work_order) -> dict:
	data = get_stock_entry_data(work_order)

	available_materials = {}
	for row in data:
		key = (row.item_code, row.warehouse)
		if row.purpose != "Material Transfer for Manufacture":
			key = (row.item_code, row.s_warehouse)

		if key not in available_materials:
			available_materials.setdefault(
				key,
				frappe._dict(
					{"item_details": row, "batch_details": defaultdict(float), "qty": 0, "serial_nos": []}
				),
			)

		item_data = available_materials[key]

		if row.purpose == "Material Transfer for Manufacture":
			item_data.qty += row.qty
			if row.batch_no:
				item_data.batch_details[row.batch_no] += row.qty

			if row.serial_no:
				item_data.serial_nos.extend(get_serial_nos(row.serial_no))
				item_data.serial_nos.sort()
		else:
			# Consume raw material qty in case of 'Manufacture' or 'Material Consumption for Manufacture'

			item_data.qty -= row.qty
			if row.batch_no:
				item_data.batch_details[row.batch_no] -= row.qty

			if row.serial_no:
				for serial_no in get_serial_nos(row.serial_no):
					item_data.serial_nos.remove(serial_no)

	return available_materials


def get_stock_entry_data(work_order):
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

	return (
		frappe.qb.from_(stock_entry)
		.from_(stock_entry_detail)
		.select(
			stock_entry_detail.item_name,
			stock_entry_detail.original_item,
			stock_entry_detail.item_code,
			stock_entry_detail.qty,
			(stock_entry_detail.t_warehouse).as_("warehouse"),
			(stock_entry_detail.s_warehouse).as_("s_warehouse"),
			stock_entry_detail.description,
			stock_entry_detail.stock_uom,
			stock_entry_detail.expense_account,
			stock_entry_detail.cost_center,
			stock_entry_detail.batch_no,
			stock_entry_detail.serial_no,
			stock_entry.purpose,
		)
		.where(
			(stock_entry.name == stock_entry_detail.parent)
			& (stock_entry.work_order == work_order)
			& (stock_entry.docstatus == 1)
			& (stock_entry_detail.s_warehouse.isnotnull())
			& (
				stock_entry.purpose.isin(
					["Manufacture", "Material Consumption for Manufacture", "Material Transfer for Manufacture"]
				)
			)
		)
		.orderby(stock_entry.creation, stock_entry_detail.item_code, stock_entry_detail.idx)
	).run(as_dict=1)
