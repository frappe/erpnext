# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe import _
from frappe.utils import cstr, cint, flt, comma_or, getdate, nowdate, formatdate, format_time
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError, get_valuation_rate
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor, get_reserved_qty_for_so
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.batch.batch import get_batch_no, set_batch_nos, get_batch_qty
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, add_additional_cost
from erpnext.stock.utils import get_bin
from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit, get_serial_nos

import json

from six import string_types, itervalues, iteritems

class IncorrectValuationRateError(frappe.ValidationError): pass
class DuplicateEntryForWorkOrderError(frappe.ValidationError): pass
class OperationsNotCompleteError(frappe.ValidationError): pass
class MaxSampleAlreadyRetainedError(frappe.ValidationError): pass

from erpnext.controllers.stock_controller import StockController

form_grid_templates = {
	"items": "templates/form_grid/stock_entry_grid.html"
}

class StockEntry(StockController):
	def get_feed(self):
		return _("From {0} to {1}").format(self.from_warehouse, self.to_warehouse)

	def onload(self):
		for item in self.get("items"):
			item.update(get_bin_details(item.item_code, item.s_warehouse))

	def validate(self):
		self.pro_doc = frappe._dict()
		if self.work_order:
			self.pro_doc = frappe.get_doc('Work Order', self.work_order)

		self.validate_posting_time()
		self.validate_purpose()
		self.validate_item()
		self.validate_qty()
		self.set_transfer_qty()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse()
		self.validate_work_order()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_with_material_request()
		self.validate_batch()
		self.validate_inspection()
		self.validate_fg_completed_qty()
		self.set_job_card_data()

		if not self.from_bom:
			self.fg_completed_qty = 0.0

		if self._action == 'submit':
			self.make_batches('t_warehouse')
		else:
			set_batch_nos(self, 's_warehouse')

		self.set_incoming_rate()
		self.set_actual_qty()
		self.calculate_rate_and_amount(update_finished_item_rate=False)

	def on_submit(self):

		self.update_stock_ledger()

		update_serial_nos_after_submit(self, "items")
		self.update_work_order()
		self.validate_purchase_order()
		if self.purchase_order and self.purpose == "Subcontract":
			self.update_purchase_order_supplied_items()
		self.make_gl_entries()
		self.update_cost_in_project()
		self.validate_reserved_serial_no_consumption()
		if self.work_order and self.purpose == "Manufacture":
			self.update_so_in_serial_number()

	def on_cancel(self):

		if self.purchase_order and self.purpose == "Subcontract":
			self.update_purchase_order_supplied_items()

		if self.work_order and self.purpose == "Material Consumption for Manufacture":
			self.validate_work_order_status()
		else:
			self.update_work_order()

		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()
		self.update_cost_in_project()

	def set_job_card_data(self):
		if self.job_card and not self.work_order:
			data = frappe.db.get_value('Job Card',
				self.job_card, ['for_quantity', 'work_order', 'bom_no'], as_dict=1)
			self.fg_completed_qty = data.for_quantity
			self.work_order = data.work_order
			self.from_bom = 1
			self.bom_no = data.bom_no

	def validate_work_order_status(self):
		pro_doc = frappe.get_doc("Work Order", self.work_order)
		if pro_doc.status == 'Completed':
			frappe.throw(_("Cannot cancel transaction for Completed Work Order."))

	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer", "Material Transfer for Manufacture",
			"Manufacture", "Repack", "Subcontract", "Material Consumption for Manufacture"]
		if self.purpose not in valid_purposes:
			frappe.throw(_("Purpose must be one of {0}").format(comma_or(valid_purposes)))

	def set_transfer_qty(self):
		for item in self.get("items"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx))
			if not flt(item.conversion_factor):
				frappe.throw(_("Row {0}: UOM Conversion Factor is mandatory").format(item.idx))
			item.transfer_qty = flt(flt(item.qty) * flt(item.conversion_factor),
				self.precision("transfer_qty", item))

	def update_cost_in_project(self):
		if self.project:
			amount = frappe.db.sql(""" select ifnull(sum(sed.amount), 0)
				from
					`tabStock Entry` se, `tabStock Entry Detail` sed
				where
					se.docstatus = 1 and se.project = %s and sed.parent = se.name
					and (sed.t_warehouse is null or sed.t_warehouse = '')""", self.project, as_list=1)

			amount = amount[0][0] if amount else 0
			additional_costs = frappe.db.sql(""" select ifnull(sum(sed.amount), 0)
				from
					`tabStock Entry` se, `tabLanded Cost Taxes and Charges` sed
				where
					se.docstatus = 1 and se.project = %s and sed.parent = se.name
					and se.purpose = 'Manufacture'""", self.project, as_list=1)

			additional_cost_amt = additional_costs[0][0] if additional_costs else 0

			amount += additional_cost_amt
			frappe.db.set_value('Project', self.project, 'total_consumed_material_cost', amount)

	def validate_item(self):
		stock_items = self.get_stock_items()
		serialized_items = self.get_serialized_items()
		for item in self.get("items"):
			if item.item_code not in stock_items:
				frappe.throw(_("{0} is not a stock Item").format(item.item_code))

			item_details = self.get_item_details(frappe._dict(
				{"item_code": item.item_code, "company": self.company,
				"project": self.project, "uom": item.uom, 's_warehouse': item.s_warehouse}),
				for_update=True)

			for f in ("uom", "stock_uom", "description", "item_name", "expense_account",
				"cost_center", "conversion_factor"):
					if f in ["stock_uom", "conversion_factor"] or not item.get(f):
						item.set(f, item_details.get(f))

			if not item.transfer_qty and item.qty:
				item.transfer_qty = item.qty * item.conversion_factor

			if (self.purpose in ("Material Transfer", "Material Transfer for Manufacture")
				and not item.serial_no
				and item.item_code in serialized_items):
				frappe.throw(_("Row #{0}: Please specify Serial No for Item {1}").format(item.idx, item.item_code),
					frappe.MandatoryError)

	def validate_qty(self):
		manufacture_purpose = ["Manufacture", "Material Consumption for Manufacture"]

		if self.purpose in manufacture_purpose and self.work_order:
			if not frappe.get_value('Work Order', self.work_order, 'skip_transfer'):
				item_code = []
				for item in self.items:
					if cstr(item.t_warehouse) == '':
						req_items = frappe.get_all('Work Order Item',
										filters={'parent': self.work_order, 'item_code': item.item_code}, fields=["item_code"])

						transferred_materials = frappe.db.sql("""
									select
										sum(qty) as qty
									from `tabStock Entry` se,`tabStock Entry Detail` sed
									where
										se.name = sed.parent and se.docstatus=1 and
										(se.purpose='Material Transfer for Manufacture' or se.purpose='Manufacture')
										and sed.item_code=%s and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
								""", (item.item_code, self.work_order), as_dict=1)

						stock_qty = flt(item.qty)
						trans_qty = flt(transferred_materials[0].qty)
						if req_items:
							if stock_qty > trans_qty:
								item_code.append(item.item_code)

	def validate_fg_completed_qty(self):
		if self.purpose == "Manufacture" and self.work_order:
			production_item = frappe.get_value('Work Order', self.work_order, 'production_item')
			for item in self.items:
				if item.item_code == production_item and item.qty != self.fg_completed_qty:
					frappe.throw(_("Finished product quantity <b>{0}</b> and For Quantity <b>{1}</b> cannot be different").format(item.qty, self.fg_completed_qty))

	def validate_warehouse(self):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = ["Material Issue", "Material Transfer", "Subcontract", "Material Transfer for Manufacture",
							"Material Consumption for Manufacture"]
		target_mandatory = ["Material Receipt", "Material Transfer", "Subcontract", "Material Transfer for Manufacture",]

		validate_for_manufacture_repack = any([d.bom_no for d in self.get("items")])

		if self.purpose in source_mandatory and self.purpose not in target_mandatory:
			self.to_warehouse = None
			for d in self.get('items'):
				d.t_warehouse = None
		elif self.purpose in target_mandatory and self.purpose not in source_mandatory:
			self.from_warehouse = None
			for d in self.get('items'):
				d.s_warehouse = None

		for d in self.get('items'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.from_warehouse
				d.t_warehouse = self.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				frappe.throw(_("Atleast one warehouse is mandatory"))

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

			if self.purpose in ["Manufacture", "Repack"]:
				if validate_for_manufacture_repack:
					if d.bom_no:
						d.s_warehouse = None

						if not d.t_warehouse:
							frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

						elif self.pro_doc and (cstr(d.t_warehouse) != self.pro_doc.fg_warehouse and cstr(d.t_warehouse) != self.pro_doc.scrap_warehouse):
							frappe.throw(_("Target warehouse in row {0} must be same as Work Order").format(d.idx))

					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse) and not self.purpose == "Material Transfer for Manufacture":
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

	def validate_work_order(self):
		if self.purpose in ("Manufacture", "Material Transfer for Manufacture", "Material Consumption for Manufacture"):
			# check if work order is entered

			if (self.purpose=="Manufacture" or self.purpose=="Material Consumption for Manufacture") \
					and self.work_order:
				if not self.fg_completed_qty:
					frappe.throw(_("For Quantity (Manufactured Qty) is mandatory"))
				self.check_if_operations_completed()
				self.check_duplicate_entry_for_work_order()
		elif self.purpose != "Material Transfer":
			self.work_order = None

	def check_if_operations_completed(self):
		"""Check if Time Sheets are completed against before manufacturing to capture operating costs."""
		prod_order = frappe.get_doc("Work Order", self.work_order)
		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		for d in prod_order.get("operations"):
			total_completed_qty = flt(self.fg_completed_qty) + flt(prod_order.produced_qty)
			completed_qty = d.completed_qty + (allowance_percentage/100 * d.completed_qty)
			if total_completed_qty > flt(completed_qty):
				frappe.throw(_("Row #{0}: Operation {1} is not completed for {2} qty of finished goods in Work Order # {3}. Please update operation status via Time Logs")
					.format(d.idx, d.operation, total_completed_qty, self.work_order), OperationsNotCompleteError)

	def check_duplicate_entry_for_work_order(self):
		other_ste = [t[0] for t in frappe.db.get_values("Stock Entry",  {
			"work_order": self.work_order,
			"purpose": self.purpose,
			"docstatus": ["!=", 2],
			"name": ["!=", self.name]
		}, "name")]

		if other_ste:
			production_item, qty = frappe.db.get_value("Work Order",
				self.work_order, ["production_item", "qty"])
			args = other_ste + [production_item]
			fg_qty_already_entered = frappe.db.sql("""select sum(transfer_qty)
				from `tabStock Entry Detail`
				where parent in (%s)
					and item_code = %s
					and ifnull(s_warehouse,'')='' """ % (", ".join(["%s" * len(other_ste)]), "%s"), args)[0][0]
			if fg_qty_already_entered and fg_qty_already_entered >= qty:
				frappe.throw(_("Stock Entries already created for Work Order ")
					+ self.work_order + ":" + ", ".join(other_ste), DuplicateEntryForWorkOrderError)

	def set_incoming_rate(self):
		for d in self.items:
			if d.s_warehouse:
				args = self.get_args_for_incoming_rate(d)
				d.basic_rate = get_incoming_rate(args)
			elif d.allow_zero_valuation_rate and not d.s_warehouse:
				d.basic_rate = 0.0
			elif d.t_warehouse and not d.basic_rate:
				d.basic_rate = get_valuation_rate(d.item_code, d.t_warehouse,
					self.doctype, d.name, d.allow_zero_valuation_rate,
					currency=erpnext.get_company_currency(self.company))

	def set_actual_qty(self):
		allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock"))

		for d in self.get('items'):
			previous_sle = get_previous_sle({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time
			})

			# get actual stock at source warehouse
			d.actual_qty = previous_sle.get("qty_after_transaction") or 0

			# validate qty during submit
			if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and flt(d.actual_qty, d.precision("actual_qty")) < flt(d.transfer_qty, d.precision("actual_qty")):
				frappe.throw(_("Row {0}: Qty not available for {4} in warehouse {1} at posting time of the entry ({2} {3})").format(d.idx,
					frappe.bold(d.s_warehouse), formatdate(self.posting_date),
					format_time(self.posting_time), frappe.bold(d.item_code))
					+ '<br><br>' + _("Available qty is {0}, you need {1}").format(frappe.bold(d.actual_qty),
						frappe.bold(d.transfer_qty)),
					NegativeStockError, title=_('Insufficient Stock'))

	def set_serial_nos(self, work_order):
		previous_se = frappe.db.get_value("Stock Entry", {"work_order": work_order,
				"purpose": "Material Transfer for Manufacture"}, "name")

		for d in self.get('items'):
			transferred_serial_no = frappe.db.get_value("Stock Entry Detail",{"parent": previous_se,
				"item_code": d.item_code}, "serial_no")

			if transferred_serial_no:
				d.serial_no = transferred_serial_no

	def get_stock_and_rate(self):
		self.set_work_order_details()
		self.set_transfer_qty()
		self.set_actual_qty()
		self.calculate_rate_and_amount()

	def calculate_rate_and_amount(self, force=False,
			update_finished_item_rate=True, raise_error_if_no_rate=True):
		self.set_basic_rate(force, update_finished_item_rate, raise_error_if_no_rate)
		self.distribute_additional_costs()
		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()

	def set_basic_rate(self, force=False, update_finished_item_rate=True, raise_error_if_no_rate=True):
		"""get stock and incoming rate on posting date"""
		raw_material_cost = 0.0
		scrap_material_cost = 0.0
		fg_basic_rate = 0.0

		for d in self.get('items'):
			if d.t_warehouse: fg_basic_rate = flt(d.basic_rate)
			args = self.get_args_for_incoming_rate(d)

			# get basic rate
			if not d.bom_no:
				if (not flt(d.basic_rate) and not d.allow_zero_valuation_rate) or d.s_warehouse or force:
					basic_rate = flt(get_incoming_rate(args, raise_error_if_no_rate), self.precision("basic_rate", d))
					if basic_rate > 0:
						d.basic_rate = basic_rate

				d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))
				if not d.t_warehouse:
					raw_material_cost += flt(d.basic_amount)

			# get scrap items basic rate
			if d.bom_no:
				if not flt(d.basic_rate) and not d.allow_zero_valuation_rate and \
					getattr(self, "pro_doc", frappe._dict()).scrap_warehouse == d.t_warehouse:
					basic_rate = flt(get_incoming_rate(args, raise_error_if_no_rate),
						self.precision("basic_rate", d))
					if basic_rate > 0:
						d.basic_rate = basic_rate
					d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

				if getattr(self, "pro_doc", frappe._dict()).scrap_warehouse == d.t_warehouse:

					scrap_material_cost += flt(d.basic_amount)

		number_of_fg_items = len([t.t_warehouse for t in self.get("items") if t.t_warehouse])
		if (fg_basic_rate == 0.0 and number_of_fg_items == 1) or update_finished_item_rate:
			self.set_basic_rate_for_finished_goods(raw_material_cost, scrap_material_cost)

	def get_args_for_incoming_rate(self, item):
		return frappe._dict({
			"item_code": item.item_code,
			"warehouse": item.s_warehouse or item.t_warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"qty": item.s_warehouse and -1*flt(item.transfer_qty) or flt(item.transfer_qty),
			"serial_no": item.serial_no,
			"voucher_type": self.doctype,
			"voucher_no": item.name,
			"company": self.company,
			"allow_zero_valuation": item.allow_zero_valuation_rate,
		})

	def set_basic_rate_for_finished_goods(self, raw_material_cost, scrap_material_cost):
		if self.purpose in ["Manufacture", "Repack"]:
			for d in self.get("items"):
				if d.transfer_qty and (d.bom_no or d.t_warehouse) and (getattr(self, "pro_doc", frappe._dict()).scrap_warehouse != d.t_warehouse):
					d.basic_rate = flt((raw_material_cost - scrap_material_cost) / flt(d.transfer_qty), d.precision("basic_rate"))
					d.basic_amount = flt((raw_material_cost - scrap_material_cost), d.precision("basic_amount"))

	def distribute_additional_costs(self):
		if self.purpose == "Material Issue":
			self.additional_costs = []

		self.total_additional_costs = sum([flt(t.amount) for t in self.get("additional_costs")])
		total_basic_amount = sum([flt(t.basic_amount) for t in self.get("items") if t.t_warehouse])

		for d in self.get("items"):
			if d.t_warehouse and total_basic_amount:
				d.additional_cost = (flt(d.basic_amount) / total_basic_amount) * self.total_additional_costs
			else:
				d.additional_cost = 0

	def update_valuation_rate(self):
		for d in self.get("items"):
			if d.transfer_qty:
				d.amount = flt(flt(d.basic_amount) + flt(d.additional_cost), d.precision("amount"))
				d.valuation_rate = flt(flt(d.basic_rate) + (flt(d.additional_cost) / flt(d.transfer_qty)),
					d.precision("valuation_rate"))

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
		if self.purpose not in ['Manufacture', 'Repack']:
			self.total_amount = sum([flt(item.amount) for item in self.get("items")])

	def validate_purchase_order(self):
		"""Throw exception if more raw material is transferred against Purchase Order than in
		the raw materials supplied table"""
		backflush_raw_materials_based_on = frappe.db.get_single_value("Buying Settings",
			"backflush_raw_materials_of_subcontract_based_on")

		if (self.purpose == "Subcontract" and self.purchase_order and
			backflush_raw_materials_based_on == 'BOM'):
			purchase_order = frappe.get_doc("Purchase Order", self.purchase_order)
			for se_item in self.items:
				item_code = se_item.original_item or se_item.item_code
				precision = cint(frappe.db.get_default("float_precision")) or 3
				total_allowed = sum([flt(d.required_qty) for d in purchase_order.supplied_items \
					if d.rm_item_code == item_code])
				if not total_allowed:
					frappe.throw(_("Item {0} not found in 'Raw Materials Supplied' table in Purchase Order {1}")
						.format(se_item.item_code, self.purchase_order))
				total_supplied = frappe.db.sql("""select sum(transfer_qty)
					from `tabStock Entry Detail`, `tabStock Entry`
					where `tabStock Entry`.purchase_order = %s
						and `tabStock Entry`.docstatus = 1
						and `tabStock Entry Detail`.item_code = %s
						and `tabStock Entry Detail`.parent = `tabStock Entry`.name""",
							(self.purchase_order, se_item.item_code))[0][0]

				if flt(total_supplied, precision) > flt(total_allowed, precision):
					frappe.throw(_("Row {0}# Item {1} cannot be transferred more than {2} against Purchase Order {3}")
						.format(se_item.idx, se_item.item_code, total_allowed, self.purchase_order))

	def validate_bom(self):
		for d in self.get('items'):
			if d.bom_no and (d.t_warehouse != getattr(self, "pro_doc", frappe._dict()).scrap_warehouse):
				item_code = d.original_item or d.item_code
				validate_bom_no(item_code, d.bom_no)

	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		items_with_target_warehouse = []
		allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		for d in self.get('items'):
			if self.purpose != "Subcontract" and d.bom_no and flt(d.transfer_qty) > flt(self.fg_completed_qty) and (d.t_warehouse != getattr(self, "pro_doc", frappe._dict()).scrap_warehouse):
				frappe.throw(_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}"). \
					format(d.idx, d.transfer_qty, self.fg_completed_qty))

			if self.work_order and self.purpose == "Manufacture" and d.t_warehouse:
				items_with_target_warehouse.append(d.item_code)

		if self.work_order and self.purpose == "Manufacture":
			production_item, wo_qty = frappe.db.get_value("Work Order",
				self.work_order, ["production_item", "qty"])

			allowed_qty = wo_qty + (allowance_percentage/100 * wo_qty)
			if self.fg_completed_qty > allowed_qty:
				frappe.throw(_("For quantity {0} should not be grater than work order quantity {1}")
					.format(flt(self.fg_completed_qty), wo_qty))

			if production_item not in items_with_target_warehouse:
				frappe.throw(_("Finished Item {0} must be entered for Manufacture type entry")
					.format(production_item))

	def update_stock_ledger(self):
		sl_entries = []

		# make sl entries for source warehouse first, then do for target warehouse
		for d in self.get('items'):
			if cstr(d.s_warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.s_warehouse),
					"actual_qty": -flt(d.transfer_qty),
					"incoming_rate": 0
				}))

		for d in self.get('items'):
			if cstr(d.t_warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.t_warehouse),
					"actual_qty": flt(d.transfer_qty),
					"incoming_rate": flt(d.valuation_rate)
				}))

		# On cancellation, make stock ledger entry for
		# target warehouse first, to update serial no values properly

			# if cstr(d.s_warehouse) and self.docstatus == 2:
			# 	sl_entries.append(self.get_sl_entries(d, {
			# 		"warehouse": cstr(d.s_warehouse),
			# 		"actual_qty": -flt(d.transfer_qty),
			# 		"incoming_rate": 0
			# 	}))

		if self.docstatus == 2:
			sl_entries.reverse()

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

	def get_gl_entries(self, warehouse_account):
		expenses_included_in_valuation = self.get_company_default("expenses_included_in_valuation")

		gl_entries = super(StockEntry, self).get_gl_entries(warehouse_account)

		for d in self.get("items"):
			additional_cost = flt(d.additional_cost, d.precision("additional_cost"))
			if additional_cost:
				gl_entries.append(self.get_gl_dict({
					"account": expenses_included_in_valuation,
					"against": d.expense_account,
					"cost_center": d.cost_center,
					"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
					"credit": additional_cost
				}))

				gl_entries.append(self.get_gl_dict({
					"account": d.expense_account,
					"against": expenses_included_in_valuation,
					"cost_center": d.cost_center,
					"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
					"credit": -1 * additional_cost # put it as negative credit instead of debit purposefully
				}))

		return gl_entries

	def update_work_order(self):
		def _validate_work_order(pro_doc):
			if flt(pro_doc.docstatus) != 1:
				frappe.throw(_("Work Order {0} must be submitted").format(self.work_order))

			if pro_doc.status == 'Stopped':
				frappe.throw(_("Transaction not allowed against stopped Work Order {0}").format(self.work_order))

		if self.job_card:
			job_doc = frappe.get_doc('Job Card', self.job_card)
			job_doc.set_transferred_qty(update_status=True)

		if self.work_order:
			pro_doc = frappe.get_doc("Work Order", self.work_order)
			_validate_work_order(pro_doc)
			pro_doc.run_method("update_status")
			if self.fg_completed_qty:
				pro_doc.run_method("update_work_order_qty")
				if self.purpose == "Manufacture":
					pro_doc.run_method("update_planned_qty")

	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql("""select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
				i.has_batch_no, i.sample_quantity, i.has_serial_no,
				id.expense_account, id.buying_cost_center
			from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
			where i.name=%s
				and i.disabled=0
				and (i.end_of_life is null or i.end_of_life='0000-00-00' or i.end_of_life > %s)""",
			(self.company, args.get('item_code'), nowdate()), as_dict = 1)

		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		item = item[0]
		item_group_defaults = get_item_group_defaults(item.name, self.company)

		ret = frappe._dict({
			'uom'			      	: item.stock_uom,
			'stock_uom'			: item.stock_uom,
			'description'		  	: item.description,
			'image'				: item.image,
			'item_name' 		  	: item.item_name,
			'expense_account'		: args.get("expense_account"),
			'cost_center'			: get_default_cost_center(args, item, item_group_defaults),
			'qty'				: args.get("qty"),
			'transfer_qty'			: args.get('qty'),
			'conversion_factor'		: 1,
			'batch_no'			: '',
			'actual_qty'			: 0,
			'basic_rate'			: 0,
			'serial_no'			: '',
			'has_serial_no'			: item.has_serial_no,
			'has_batch_no'			: item.has_batch_no,
			'sample_quantity'		: item.sample_quantity
		})
		for d in [["Account", "expense_account", "default_expense_account"],
			["Cost Center", "cost_center", "cost_center"]]:
				company = frappe.db.get_value(d[0], ret.get(d[1]), "company")
				if not ret[d[1]] or (company and self.company != company):
					ret[d[1]] = frappe.get_cached_value('Company',  self.company,  d[2]) if d[2] else None

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty')))

		if not ret["expense_account"]:
			ret["expense_account"] = frappe.get_cached_value('Company',  self.company,  "stock_adjustment_account")

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get('warehouse') else {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		if (args.get('s_warehouse', None) and args.get('qty') and
			ret.get('has_batch_no') and not args.get('batch_no')):
			args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret

	def get_items(self):
		self.set('items', [])
		self.validate_work_order()

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		self.set_work_order_details()

		if self.bom_no:

			if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
					"Subcontract", "Material Transfer for Manufacture", "Material Consumption for Manufacture"]:

				if self.work_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials()
					if self.to_warehouse and self.pro_doc:
						for item in itervalues(item_dict):
							item["to_warehouse"] = self.pro_doc.wip_warehouse
					self.add_to_stock_entry_detail(item_dict)

				elif (self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
					and not self.pro_doc.skip_transfer and frappe.db.get_single_value("Manufacturing Settings",
					"backflush_raw_materials_based_on")== "Material Transferred for Manufacture"):
					self.get_transfered_raw_materials()

				elif self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture") and \
					frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "BOM" and \
					frappe.db.get_single_value("Manufacturing Settings", "material_consumption")== 1:
					self.get_unconsumed_raw_materials()

				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)

					#Get PO Supplied Items Details
					if self.purchase_order and self.purpose == "Subcontract":
						#Get PO Supplied Items Details
						item_wh = frappe._dict(frappe.db.sql("""
							select rm_item_code, reserve_warehouse
							from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
							where po.name = poitemsup.parent
								and po.name = %s""",self.purchase_order))

					for item in itervalues(item_dict):
						if self.pro_doc and (cint(self.pro_doc.from_wip_warehouse) or not self.pro_doc.skip_transfer):
							item["from_warehouse"] = self.pro_doc.wip_warehouse
						#Get Reserve Warehouse from PO
						if self.purchase_order and self.purpose=="Subcontract":
							item["from_warehouse"] = item_wh.get(item.item_code)
						item["to_warehouse"] = self.to_warehouse if self.purpose=="Subcontract" else ""

					self.add_to_stock_entry_detail(item_dict)

					if self.purpose != "Subcontract":
						scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
						for item in itervalues(scrap_item_dict):
							if self.pro_doc and self.pro_doc.scrap_warehouse:
								item["to_warehouse"] = self.pro_doc.scrap_warehouse

						self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

			# fetch the serial_no of the first stock entry for the second stock entry
			if self.work_order and self.purpose == "Manufacture":
				self.set_serial_nos(self.work_order)
				work_order = frappe.get_doc('Work Order', self.work_order)
				add_additional_cost(self, work_order)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.load_items_from_bom()

		self.set_actual_qty()
		self.calculate_rate_and_amount(raise_error_if_no_rate=False)

	def set_work_order_details(self):
		if not getattr(self, "pro_doc", None):
			self.pro_doc = frappe._dict()

		if self.work_order:
			# common validations
			if not self.pro_doc:
				self.pro_doc = frappe.get_doc('Work Order', self.work_order)

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

		self.add_to_stock_entry_detail({
			item.name: {
				"to_warehouse": to_warehouse,
				"from_warehouse": "",
				"qty": self.fg_completed_qty,
				"item_name": item.item_name,
				"description": item.description,
				"stock_uom": item.stock_uom,
				"expense_account": item.get("expense_account"),
				"cost_center": item.get("buying_cost_center"),
			}
		}, bom_no = self.bom_no)

	def get_bom_raw_materials(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = self.use_multi_level_bom)

		used_alternative_items = get_used_alternative_items(work_order = self.work_order)
		for item in itervalues(item_dict):
			# if source warehouse presents in BOM set from_warehouse as bom source_warehouse
			if item["allow_alternative_item"]:
				item["allow_alternative_item"] = frappe.db.get_value('Work Order',
					self.work_order, "allow_alternative_item")

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
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = 0, fetch_scrap_items = 1)

		for item in itervalues(item_dict):
			item.from_warehouse = ""
		return item_dict

	def get_unconsumed_raw_materials(self):
		wo = frappe.get_doc("Work Order", self.work_order)
		wo_items = frappe.get_all('Work Order Item',
			filters={'parent': self.work_order},
			fields=["item_code", "required_qty", "consumed_qty"]
			)

		for item in wo_items:
			qty = item.required_qty

			item_account_details = get_item_defaults(item.item_code, self.company)
			# Take into account consumption if there are any.
			if self.purpose == 'Manufacture':
				req_qty_each = flt(item.required_qty / wo.qty)
				if (flt(item.consumed_qty) != 0):
					remaining_qty = flt(item.consumed_qty) - (flt(wo.produced_qty) * req_qty_each)
					exhaust_qty = req_qty_each * wo.produced_qty
					if remaining_qty > exhaust_qty :
						if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
							qty =0
						else:
							qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
				else:
					qty = req_qty_each * flt(self.fg_completed_qty)

			if qty > 0:
				self.add_to_stock_entry_detail({
					item.item_code: {
						"from_warehouse": wo.wip_warehouse,
						"to_warehouse": "",
						"qty": qty,
						"item_name": item.item_name,
						"description": item.description,
						"stock_uom": item_account_details.stock_uom,
						"expense_account": item_account_details.get("expense_account"),
						"cost_center": item_account_details.get("buying_cost_center"),
					}
				})

	def get_transfered_raw_materials(self):
		transferred_materials = frappe.db.sql("""
			select
				item_name, original_item, item_code, sum(qty) as qty, sed.t_warehouse as warehouse,
				description, stock_uom, expense_account, cost_center
			from `tabStock Entry` se,`tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1 and se.purpose='Material Transfer for Manufacture'
				and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
			group by sed.item_code, sed.t_warehouse
		""", self.work_order, as_dict=1)

		materials_already_backflushed = frappe.db.sql("""
			select
				item_code, sed.s_warehouse as warehouse, sum(qty) as qty
			from
				`tabStock Entry` se, `tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1
				and (se.purpose='Manufacture' or se.purpose='Material Consumption for Manufacture')
				and se.work_order= %s and ifnull(sed.s_warehouse, '') != ''
			group by sed.item_code, sed.s_warehouse
		""", self.work_order, as_dict=1)

		backflushed_materials= {}
		for d in materials_already_backflushed:
			backflushed_materials.setdefault(d.item_code,[]).append({d.warehouse: d.qty})

		po_qty = frappe.db.sql("""select qty, produced_qty, material_transferred_for_manufacturing from
			`tabWork Order` where name=%s""", self.work_order, as_dict=1)[0]

		manufacturing_qty = flt(po_qty.qty)
		produced_qty = flt(po_qty.produced_qty)
		trans_qty = flt(po_qty.material_transferred_for_manufacturing)

		for item in transferred_materials:
			qty= item.qty
			item_code = item.original_item or item.item_code
			req_items = frappe.get_all('Work Order Item',
				filters={'parent': self.work_order, 'item_code': item_code},
				fields=["required_qty", "consumed_qty"]
				)
			req_qty = flt(req_items[0].required_qty)
			req_qty_each = flt(req_qty / manufacturing_qty)
			consumed_qty = flt(req_items[0].consumed_qty)

			if trans_qty and manufacturing_qty >= (produced_qty + flt(self.fg_completed_qty)):
				if qty >= req_qty:
					qty = (req_qty/trans_qty) * flt(self.fg_completed_qty)
				else:
					qty = qty - consumed_qty

				if self.purpose == 'Manufacture':
					# If Material Consumption is booked, must pull only remaining components to finish product
					if consumed_qty != 0:
						remaining_qty = consumed_qty - (produced_qty * req_qty_each)
						exhaust_qty = req_qty_each * produced_qty
						if remaining_qty > exhaust_qty :
							if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
								qty =0
							else:
								qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
					else:
						qty = req_qty_each * flt(self.fg_completed_qty)


			elif backflushed_materials.get(item.item_code):
				for d in backflushed_materials.get(item.item_code):
					if d.get(item.warehouse):
						if (qty > req_qty):
							qty = req_qty
							qty-= d.get(item.warehouse)

			if qty > 0:
				self.add_to_stock_entry_detail({
					item.item_code: {
						"from_warehouse": item.warehouse,
						"to_warehouse": "",
						"qty": qty,
						"item_name": item.item_name,
						"description": item.description,
						"stock_uom": item.stock_uom,
						"expense_account": item.expense_account,
						"cost_center": item.buying_cost_center,
						"original_item": item.original_item
					}
				})

	def get_pending_raw_materials(self):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_dict = self.get_pro_order_required_items()
		max_qty = flt(self.pro_doc.qty)
		for item, item_details in iteritems(item_dict):
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if desire_to_transfer <= pending_to_issue:
				item_dict[item]["qty"] = desire_to_transfer
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0

		# delete items with 0 qty
		for item in item_dict.keys():
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict

	def get_pro_order_required_items(self):
		item_dict = frappe._dict()
		pro_order = frappe.get_doc("Work Order", self.work_order)
		if not frappe.db.get_value("Warehouse", pro_order.wip_warehouse, "is_group"):
			wip_warehouse = pro_order.wip_warehouse
		else:
			wip_warehouse = None

		for d in pro_order.get("required_items"):
			if (flt(d.required_qty) > flt(d.transferred_qty) and
				(d.include_item_in_manufacturing or self.purpose != "Material Transfer for Manufacture")):
				item_row = d.as_dict()
				if d.source_warehouse and not frappe.db.get_value("Warehouse", d.source_warehouse, "is_group"):
					item_row["from_warehouse"] = d.source_warehouse

				item_row["to_warehouse"] = wip_warehouse
				if item_row["allow_alternative_item"]:
					item_row["allow_alternative_item"] = pro_order.allow_alternative_item

				item_dict.setdefault(d.item_code, item_row)

		return item_dict

	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		expense_account, cost_center = frappe.db.get_values("Company", self.company, \
			["default_expense_account", "cost_center"])[0]

		for d in item_dict:
			stock_uom = item_dict[d].get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

			se_child = self.append('items')
			se_child.s_warehouse = item_dict[d].get("from_warehouse")
			se_child.t_warehouse = item_dict[d].get("to_warehouse")
			se_child.item_code = item_dict[d].get('item_code') or cstr(d)
			se_child.item_name = item_dict[d]["item_name"]
			se_child.description = item_dict[d]["description"]
			se_child.uom = stock_uom
			se_child.stock_uom = stock_uom
			se_child.qty = flt(item_dict[d]["qty"], se_child.precision("qty"))
			se_child.expense_account = item_dict[d].get("expense_account") or expense_account
			se_child.cost_center = item_dict[d].get("cost_center") or cost_center
			se_child.allow_alternative_item = item_dict[d].get("allow_alternative_item", 0)
			se_child.subcontracted_item = item_dict[d].get("main_item_code")
			se_child.original_item = item_dict[d].get("original_item")

			if item_dict[d].get("idx"):
				se_child.idx = item_dict[d].get("idx")

			if se_child.s_warehouse==None:
				se_child.s_warehouse = self.from_warehouse
			if se_child.t_warehouse==None:
				se_child.t_warehouse = self.to_warehouse

			# in stock uom
			se_child.transfer_qty = flt(item_dict[d]["qty"], se_child.precision("qty"))
			se_child.conversion_factor = 1.00

			# to be assigned for finished item
			se_child.bom_no = bom_no

	def validate_with_material_request(self):
		for item in self.get("items"):
			if item.material_request:
				mreq_item = frappe.db.get_value("Material Request Item",
					{"name": item.material_request_item, "parent": item.material_request},
					["item_code", "warehouse", "idx"], as_dict=True)
				if mreq_item.item_code != item.item_code or \
				mreq_item.warehouse != (item.s_warehouse if self.purpose== "Material Issue" else item.t_warehouse):
					frappe.throw(_("Item or Warehouse for row {0} does not match Material Request").format(item.idx),
						frappe.MappingMismatchError)

	def validate_batch(self):
		if self.purpose in ["Material Transfer for Manufacture", "Manufacture", "Repack", "Subcontract", "Material Issue"]:
			for item in self.get("items"):
				if item.batch_no:
					disabled = frappe.db.get_value("Batch", item.batch_no, "disabled")
					if disabled == 0:
						expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
						if expiry_date:
							if getdate(self.posting_date) > getdate(expiry_date):
								frappe.throw(_("Batch {0} of Item {1} has expired.")
									.format(item.batch_no, item.item_code))
					else:
						frappe.throw(_("Batch {0} of Item {1} is disabled.")
							.format(item.batch_no, item.item_code))

	def update_purchase_order_supplied_items(self):
		#Get PO Supplied Items Details
		item_wh = frappe._dict(frappe.db.sql("""
			select rm_item_code, reserve_warehouse
			from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
			where po.name = poitemsup.parent
			and po.name = %s""", self.purchase_order))

		#Update reserved sub contracted quantity in bin based on Supplied Item Details
		for d in self.get("items"):
			item_code = d.get('original_item') or d.get('item_code')
			reserve_warehouse = item_wh.get(item_code)
			stock_bin = get_bin(item_code, reserve_warehouse)
			stock_bin.update_reserved_qty_for_sub_contracting()

	def update_so_in_serial_number(self):
		so_name, item_code = frappe.db.get_value("Work Order", self.work_order, ["sales_order", "production_item"])
		if so_name and item_code:
			qty_to_reserve = get_reserved_qty_for_so(so_name, item_code)
			if qty_to_reserve:
				reserved_qty = frappe.db.sql("""select count(name) from `tabSerial No` where item_code=%s and
					sales_order=%s""", (item_code, so_name))
				if reserved_qty and reserved_qty[0][0]:
					qty_to_reserve -= reserved_qty[0][0]
				if qty_to_reserve > 0:
					for item in self.items:
						if item.item_code == item_code:
							serial_nos = (item.serial_no).split("\n")
							for serial_no in serial_nos:
								if qty_to_reserve > 0:
									frappe.db.set_value("Serial No", serial_no, "sales_order", so_name)
									qty_to_reserve -=1

	def validate_reserved_serial_no_consumption(self):
		for item in self.items:
			if item.s_warehouse and not item.t_warehouse and item.serial_no:
				for sr in get_serial_nos(item.serial_no):
					sales_order = frappe.db.get_value("Serial No", sr, "sales_order")
					if sales_order:
						frappe.throw(_("Item {0} (Serial No: {1}) cannot be consumed as is reserverd\
						 to fullfill Sales Order {2}.").format(item.item_code, sr, sales_order))

@frappe.whitelist()
def move_sample_to_retention_warehouse(company, items):
	if isinstance(items, string_types):
		items = json.loads(items)
	retention_warehouse = frappe.db.get_single_value('Stock Settings', 'sample_retention_warehouse')
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.company = company
	stock_entry.purpose = "Material Transfer"
	for item in items:
		if item.get('sample_quantity') and item.get('batch_no'):
			sample_quantity = validate_sample_quantity(item.get('item_code'), item.get('sample_quantity'),
				item.get('transfer_qty') or item.get('qty'), item.get('batch_no'))
			if sample_quantity:
				sample_serial_nos = ''
				if item.get('serial_no'):
					serial_nos = (item.get('serial_no')).split()
					if serial_nos and len(serial_nos) > item.get('sample_quantity'):
						serial_no_list = serial_nos[:-(len(serial_nos)-item.get('sample_quantity'))]
						sample_serial_nos = '\n'.join(serial_no_list)

				stock_entry.append("items", {
					"item_code": item.get('item_code'),
					"s_warehouse": item.get('t_warehouse'),
					"t_warehouse": retention_warehouse,
					"qty": item.get('sample_quantity'),
					"basic_rate": item.get('valuation_rate'),
					'uom': item.get('uom'),
					'stock_uom': item.get('stock_uom'),
					"conversion_factor": 1.0,
					"serial_no": sample_serial_nos,
					'batch_no': item.get('batch_no')
				})
	if stock_entry.get('items'):
		return stock_entry.as_dict()

@frappe.whitelist()
def get_work_order_details(work_order):
	work_order = frappe.get_doc("Work Order", work_order)
	pending_qty_to_produce = flt(work_order.qty) - flt(work_order.produced_qty)

	return {
		"from_bom": 1,
		"bom_no": work_order.bom_no,
		"use_multi_level_bom": work_order.use_multi_level_bom,
		"wip_warehouse": work_order.wip_warehouse,
		"fg_warehouse": work_order.fg_warehouse,
		"fg_completed_qty": pending_qty_to_produce,
		"additional_costs": get_additional_costs(work_order, fg_qty=pending_qty_to_produce)
	}

def get_additional_costs(work_order=None, bom_no=None, fg_qty=None):
	additional_costs = []
	operating_cost_per_unit = get_operating_cost_per_unit(work_order, bom_no)
	if operating_cost_per_unit:
		additional_costs.append({
			"description": "Operating Cost as per Work Order / BOM",
			"amount": operating_cost_per_unit * flt(fg_qty)
		})

	if work_order and work_order.additional_operating_cost and work_order.qty:
		additional_operating_cost_per_unit = \
			flt(work_order.additional_operating_cost) / flt(work_order.qty)

		additional_costs.append({
			"description": "Additional Operating Cost",
			"amount": additional_operating_cost_per_unit * flt(fg_qty)
		})

	return additional_costs

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

	return operating_cost_per_unit

def get_used_alternative_items(purchase_order=None, work_order=None):
	cond = ""

	if purchase_order:
		cond = "and ste.purpose = 'Subcontract' and ste.purchase_order = '{0}'".format(purchase_order)
	elif work_order:
		cond = "and ste.purpose = 'Material Transfer for Manufacture' and ste.work_order = '{0}'".format(work_order)

	if not cond: return {}

	used_alternative_items = {}
	data = frappe.db.sql(""" select sted.original_item, sted.uom, sted.conversion_factor,
			sted.item_code, sted.item_name, sted.conversion_factor,sted.stock_uom, sted.description
		from
			`tabStock Entry` ste, `tabStock Entry Detail` sted
		where
			sted.parent = ste.name and ste.docstatus = 1 and sted.original_item !=  sted.item_code
			{0} """.format(cond), as_dict=1)

	for d in data:
		used_alternative_items[d.original_item] = d

	return used_alternative_items

@frappe.whitelist()
def get_uom_details(item_code, uom, qty):
	"""Returns dict `{"conversion_factor": [value], "transfer_qty": qty * [value]}`

	:param args: dict with `item_code`, `uom` and `qty`"""
	conversion_factor = get_conversion_factor(item_code, uom).get("conversion_factor")

	if not conversion_factor:
		frappe.msgprint(_("UOM coversion factor required for UOM: {0} in Item: {1}")
			.format(uom, item_code))
		ret = {'uom' : ''}
	else:
		ret = {
			'conversion_factor'		: flt(conversion_factor),
			'transfer_qty'			: flt(qty) * flt(conversion_factor)
		}
	return ret

@frappe.whitelist()
def get_expired_batch_items():
	return frappe.db.sql("""select b.item, sum(sle.actual_qty) as qty, sle.batch_no, sle.warehouse, sle.stock_uom\
	from `tabBatch` b, `tabStock Ledger Entry` sle
	where b.expiry_date <= %s
	and b.expiry_date is not NULL
	and b.batch_id = sle.batch_no
	group by sle.warehouse, sle.item_code, sle.batch_no""",(nowdate()), as_dict=1)

@frappe.whitelist()
def get_warehouse_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	ret = {}
	if args.warehouse and args.item_code:
		args.update({
			"posting_date": args.posting_date,
			"posting_time": args.posting_time,
		})
		ret = {
			"actual_qty" : get_previous_sle(args).get("qty_after_transaction") or 0,
			"basic_rate" : get_incoming_rate(args)
		}
	return ret

@frappe.whitelist()
def validate_sample_quantity(item_code, sample_quantity, qty, batch_no = None):
	if cint(qty) < cint(sample_quantity):
		frappe.throw(_("Sample quantity {0} cannot be more than received quantity {1}").format(sample_quantity, qty))
	retention_warehouse = frappe.db.get_single_value('Stock Settings', 'sample_retention_warehouse')
	retainted_qty = 0
	if batch_no:
		retainted_qty = get_batch_qty(batch_no, retention_warehouse, item_code)
	max_retain_qty = frappe.get_value('Item', item_code, 'sample_quantity')
	if retainted_qty >= max_retain_qty:
		frappe.msgprint(_("Maximum Samples - {0} have already been retained for Batch {1} and Item {2} in Batch {3}.").
			format(retainted_qty, batch_no, item_code, batch_no), alert=True)
		sample_quantity = 0
	qty_diff = max_retain_qty-retainted_qty
	if cint(sample_quantity) > cint(qty_diff):
		frappe.msgprint(_("Maximum Samples - {0} can be retained for Batch {1} and Item {2}.").
			format(max_retain_qty, batch_no, item_code), alert=True)
		sample_quantity = qty_diff
	return sample_quantity
