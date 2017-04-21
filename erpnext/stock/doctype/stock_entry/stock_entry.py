# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import _
from frappe.utils import cstr, cint, flt, comma_or, getdate, nowdate, formatdate, format_time
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor
from erpnext.stock.doctype.batch.batch import get_batch_no, set_batch_nos
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no
import json

class IncorrectValuationRateError(frappe.ValidationError): pass
class DuplicateEntryForProductionOrderError(frappe.ValidationError): pass
class OperationsNotCompleteError(frappe.ValidationError): pass

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
		if self.production_order:
			self.pro_doc = frappe.get_doc('Production Order', self.production_order)

		self.validate_posting_time()
		self.validate_purpose()
		self.validate_item()
		self.set_transfer_qty()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse()
		self.validate_production_order()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_with_material_request()
		self.validate_batch()

		if self._action == 'submit':
			self.make_batches('t_warehouse')
		else:
			set_batch_nos(self, 's_warehouse', True)

		self.set_actual_qty()
		self.calculate_rate_and_amount(update_finished_item_rate=False)

	def on_submit(self):
		self.update_stock_ledger()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "items")
		self.update_production_order()
		self.validate_purchase_order()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_production_order()
		self.make_gl_entries_on_cancel()

	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer", "Material Transfer for Manufacture",
			"Manufacture", "Repack", "Subcontract"]
		if self.purpose not in valid_purposes:
			frappe.throw(_("Purpose must be one of {0}").format(comma_or(valid_purposes)))

	def set_transfer_qty(self):
		for item in self.get("items"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx))
			if not flt(item.conversion_factor):
				frappe.throw(_("Row {0}: UOM Conversion Factor is mandatory").format(item.idx))
			item.transfer_qty = flt(item.qty * item.conversion_factor, self.precision("transfer_qty", item))

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

	def validate_warehouse(self):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = ["Material Issue", "Material Transfer", "Subcontract", "Material Transfer for Manufacture"]
		target_mandatory = ["Material Receipt", "Material Transfer", "Subcontract", "Material Transfer for Manufacture"]

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
							frappe.throw(_("Target warehouse in row {0} must be same as Production Order").format(d.idx))

					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse) and not self.purpose == "Material Transfer for Manufacture":
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

	def validate_production_order(self):
		if self.purpose in ("Manufacture", "Material Transfer for Manufacture"):
			# check if production order is entered

			if self.purpose=="Manufacture" and self.production_order:
				if not self.fg_completed_qty:
					frappe.throw(_("For Quantity (Manufactured Qty) is mandatory"))
				self.check_if_operations_completed()
				self.check_duplicate_entry_for_production_order()
		elif self.purpose != "Material Transfer":
			self.production_order = None

	def check_if_operations_completed(self):
		"""Check if Time Sheets are completed against before manufacturing to capture operating costs."""
		prod_order = frappe.get_doc("Production Order", self.production_order)

		for d in prod_order.get("operations"):
			total_completed_qty = flt(self.fg_completed_qty) + flt(prod_order.produced_qty)
			if total_completed_qty > flt(d.completed_qty):
				frappe.throw(_("Row #{0}: Operation {1} is not completed for {2} qty of finished goods in Production Order # {3}. Please update operation status via Time Logs")
					.format(d.idx, d.operation, total_completed_qty, self.production_order), OperationsNotCompleteError)

	def check_duplicate_entry_for_production_order(self):
		other_ste = [t[0] for t in frappe.db.get_values("Stock Entry",  {
			"production_order": self.production_order,
			"purpose": self.purpose,
			"docstatus": ["!=", 2],
			"name": ["!=", self.name]
		}, "name")]

		if other_ste:
			production_item, qty = frappe.db.get_value("Production Order",
				self.production_order, ["production_item", "qty"])
			args = other_ste + [production_item]
			fg_qty_already_entered = frappe.db.sql("""select sum(transfer_qty)
				from `tabStock Entry Detail`
				where parent in (%s)
					and item_code = %s
					and ifnull(s_warehouse,'')='' """ % (", ".join(["%s" * len(other_ste)]), "%s"), args)[0][0]

			if fg_qty_already_entered >= qty:
				frappe.throw(_("Stock Entries already created for Production Order ")
					+ self.production_order + ":" + ", ".join(other_ste), DuplicateEntryForProductionOrderError)

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
			if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and d.actual_qty < d.transfer_qty:
				frappe.throw(_("Row {0}: Qty not available for {4} in warehouse {1} at posting time of the entry ({2} {3})").format(d.idx,
					frappe.bold(d.s_warehouse), formatdate(self.posting_date),
					format_time(self.posting_time), frappe.bold(d.item_code))
					+ '<br><br>' + _("Available qty is {0}, you need {1}").format(frappe.bold(d.actual_qty),
						frappe.bold(d.transfer_qty)),
					NegativeStockError, title=_('Insufficient Stock'))

	def set_serial_nos(self, production_order):
		previous_se = frappe.db.get_value("Stock Entry", {"production_order": production_order,
				"purpose": "Material Transfer for Manufacture"}, "name")

		for d in self.get('items'):
			transferred_serial_no = frappe.db.get_value("Stock Entry Detail",{"parent": previous_se,
				"item_code": d.item_code}, "serial_no")

			if transferred_serial_no:
				d.serial_no = transferred_serial_no

	def get_stock_and_rate(self):
		self.set_production_order_details()
		self.set_transfer_qty()
		self.set_actual_qty()
		self.calculate_rate_and_amount()

	def calculate_rate_and_amount(self, force=False, update_finished_item_rate=True):
		self.set_basic_rate(force, update_finished_item_rate)
		self.distribute_additional_costs()
		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()

	def set_basic_rate(self, force=False, update_finished_item_rate=True):
		"""get stock and incoming rate on posting date"""
		raw_material_cost = 0.0
		scrap_material_cost = 0.0
		fg_basic_rate = 0.0

		for d in self.get('items'):
			if d.t_warehouse: fg_basic_rate = flt(d.basic_rate)
			args = frappe._dict({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": d.s_warehouse and -1*flt(d.transfer_qty) or flt(d.transfer_qty),
				"serial_no": d.serial_no,
			})

			# get basic rate
			if not d.bom_no:
				if not flt(d.basic_rate) or d.s_warehouse or force:
					basic_rate = flt(get_incoming_rate(args), self.precision("basic_rate", d))
					if basic_rate > 0:
						d.basic_rate = basic_rate

				d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))
				if not d.t_warehouse:
					raw_material_cost += flt(d.basic_amount)

			# get scrap items basic rate
			if d.bom_no:
				if not flt(d.basic_rate) and getattr(self, "pro_doc", frappe._dict()).scrap_warehouse == d.t_warehouse:
					basic_rate = flt(get_incoming_rate(args), self.precision("basic_rate", d))
					if basic_rate > 0:
						d.basic_rate = basic_rate
					d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

				if getattr(self, "pro_doc", frappe._dict()).scrap_warehouse == d.t_warehouse:

					scrap_material_cost += flt(d.basic_amount)

		number_of_fg_items = len([t.t_warehouse for t in self.get("items") if t.t_warehouse])
		if (fg_basic_rate == 0.0 and number_of_fg_items == 1) or update_finished_item_rate:
			self.set_basic_rate_for_finished_goods(raw_material_cost, scrap_material_cost)

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
		if self.purpose == "Subcontract" and self.purchase_order:
			purchase_order = frappe.get_doc("Purchase Order", self.purchase_order)
			for se_item in self.items:
				total_allowed = sum([flt(d.required_qty) for d in purchase_order.supplied_items \
					if d.rm_item_code == se_item.item_code])
				if not total_allowed:
					frappe.throw(_("Item {0} not found in 'Raw Materials Supplied' table in Purchase Order {1}")
						.format(se_item.item_code, self.purchase_order))
				total_supplied = frappe.db.sql("""select sum(qty)
					from `tabStock Entry Detail`, `tabStock Entry`
					where `tabStock Entry`.purchase_order = %s
						and `tabStock Entry`.docstatus = 1
						and `tabStock Entry Detail`.item_code = %s
						and `tabStock Entry Detail`.parent = `tabStock Entry`.name""",
							(self.purchase_order, se_item.item_code))[0][0]

				if total_supplied > total_allowed:
					frappe.throw(_("Not allowed to tranfer more {0} than {1} against Purchase Order {2}").format(se_item.item_code,
						total_allowed, self.purchase_order))

	def validate_bom(self):
		for d in self.get('items'):
			if d.bom_no and (d.t_warehouse != getattr(self, "pro_doc", frappe._dict()).scrap_warehouse):
				validate_bom_no(d.item_code, d.bom_no)

	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		items_with_target_warehouse = []
		for d in self.get('items'):
			if d.bom_no and flt(d.transfer_qty) != flt(self.fg_completed_qty) and (d.t_warehouse != getattr(self, "pro_doc", frappe._dict()).scrap_warehouse):
				frappe.throw(_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}"). \
					format(d.idx, d.transfer_qty, self.fg_completed_qty))

			if self.production_order and self.purpose == "Manufacture" and d.t_warehouse:
				items_with_target_warehouse.append(d.item_code)

		if self.production_order and self.purpose == "Manufacture":
			production_item = frappe.db.get_value("Production Order",
				self.production_order, "production_item")
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

	def update_production_order(self):
		def _validate_production_order(pro_doc):
			if flt(pro_doc.docstatus) != 1:
				frappe.throw(_("Production Order {0} must be submitted").format(self.production_order))

			if pro_doc.status == 'Stopped':
				frappe.throw(_("Transaction not allowed against stopped Production Order {0}").format(self.production_order))

		if self.production_order:
			pro_doc = frappe.get_doc("Production Order", self.production_order)
			_validate_production_order(pro_doc)
			pro_doc.run_method("update_status")
			if self.fg_completed_qty:
				pro_doc.run_method("update_production_order_qty")
				if self.purpose == "Manufacture":
					pro_doc.run_method("update_planned_qty")

	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql("""select stock_uom, description, image, item_name,
				expense_account, buying_cost_center, item_group, has_serial_no,
				has_batch_no
			from `tabItem`
			where name = %s
				and disabled=0
				and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %s)""",
			(args.get('item_code'), nowdate()), as_dict = 1)
		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		item = item[0]

		ret = frappe._dict({
			'uom'			      	: item.stock_uom,
			'stock_uom'			  	: item.stock_uom,
			'description'		  	: item.description,
			'image'					: item.image,
			'item_name' 		  	: item.item_name,
			'expense_account'		: args.get("expense_account"),
			'cost_center'			: get_default_cost_center(args, item),
			'qty'					: 0,
			'transfer_qty'			: 0,
			'conversion_factor'		: 1,
			'batch_no'				: '',
			'actual_qty'			: 0,
			'basic_rate'			: 0,
			'serial_no'				: '',
			'has_serial_no'			: item.has_serial_no,
			'has_batch_no'			: item.has_batch_no
		})
		for d in [["Account", "expense_account", "default_expense_account"],
			["Cost Center", "cost_center", "cost_center"]]:
				company = frappe.db.get_value(d[0], ret.get(d[1]), "company")
				if not ret[d[1]] or (company and self.company != company):
					ret[d[1]] = frappe.db.get_value("Company", self.company, d[2]) if d[2] else None

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty')))

		if not ret["expense_account"]:
			ret["expense_account"] = frappe.db.get_value("Company", self.company, "stock_adjustment_account")

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = args.get('warehouse') and get_warehouse_details(args) or {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		if (args.get('s_warehouse', None) and args.get('qty') and
			ret.get('has_batch_no') and not args.get('batch_no')):
			args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret

	def get_items(self):
		self.set('items', [])
		self.validate_production_order()

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		self.set_production_order_details()

		if self.bom_no:
			if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
					"Subcontract", "Material Transfer for Manufacture"]:
				if self.production_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials()
					if self.to_warehouse and self.pro_doc:
						for item in item_dict.values():
							item["to_warehouse"] = self.pro_doc.wip_warehouse
					self.add_to_stock_entry_detail(item_dict)

				elif self.production_order and self.purpose == "Manufacture" and \
					frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "Material Transferred for Manufacture":
					self.get_transfered_raw_materials()

				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)
					for item in item_dict.values():
						if self.pro_doc:
							item["from_warehouse"] = self.pro_doc.wip_warehouse

						item["to_warehouse"] = self.to_warehouse if self.purpose=="Subcontract" else ""

					self.add_to_stock_entry_detail(item_dict)

					scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
					for item in scrap_item_dict.values():
						if self.pro_doc and self.pro_doc.scrap_warehouse:
							item["to_warehouse"] = self.pro_doc.scrap_warehouse
					self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

			# fetch the serial_no of the first stock entry for the second stock entry
			if self.production_order and self.purpose == "Manufacture":
				self.set_serial_nos(self.production_order)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.load_items_from_bom()

		self.set_actual_qty()
		self.calculate_rate_and_amount()

	def set_production_order_details(self):
		if not getattr(self, "pro_doc", None):
			self.pro_doc = frappe._dict()

		if self.production_order:
			# common validations
			if not self.pro_doc:
				self.pro_doc = frappe.get_doc('Production Order', self.production_order)

			if self.pro_doc:
				self.bom_no = self.pro_doc.bom_no
			else:
				# invalid production order
				self.production_order = None

	def load_items_from_bom(self):
		if self.production_order:
			item_code = self.pro_doc.production_item
			to_warehouse = self.pro_doc.fg_warehouse
		else:
			item_code = frappe.db.get_value("BOM", self.bom_no, "item")
			to_warehouse = self.to_warehouse

		item = frappe.db.get_value("Item", item_code, ["item_name",
			"description", "stock_uom", "expense_account", "buying_cost_center", "name", "default_warehouse"], as_dict=1)

		if not self.production_order and not to_warehouse:
			# in case of BOM
			to_warehouse = item.default_warehouse

		self.add_to_stock_entry_detail({
			item.name: {
				"to_warehouse": to_warehouse,
				"from_warehouse": "",
				"qty": self.fg_completed_qty,
				"item_name": item.item_name,
				"description": item.description,
				"stock_uom": item.stock_uom,
				"expense_account": item.expense_account,
				"cost_center": item.buying_cost_center,
			}
		}, bom_no = self.bom_no)

	def get_bom_raw_materials(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = self.use_multi_level_bom)

		for item in item_dict.values():
			item.from_warehouse = self.from_warehouse or item.default_warehouse
		return item_dict

	def get_bom_scrap_material(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, self.company, qty=qty,
			fetch_exploded = 0, fetch_scrap_items = 1)

		for item in item_dict.values():
			item.from_warehouse = ""
		return item_dict

	def get_transfered_raw_materials(self):
		transferred_materials = frappe.db.sql("""
			select
				item_name, item_code, sum(qty) as qty, sed.t_warehouse as warehouse,
				description, stock_uom, expense_account, cost_center
			from `tabStock Entry` se,`tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1 and se.purpose='Material Transfer for Manufacture'
				and se.production_order= %s and ifnull(sed.t_warehouse, '') != ''
			group by sed.item_code, sed.t_warehouse
		""", self.production_order, as_dict=1)

		materials_already_backflushed = frappe.db.sql("""
			select
				item_code, sed.s_warehouse as warehouse, sum(qty) as qty
			from
				`tabStock Entry` se, `tabStock Entry Detail` sed
			where
				se.name = sed.parent and se.docstatus=1 and se.purpose='Manufacture'
				and se.production_order= %s and ifnull(sed.s_warehouse, '') != ''
			group by sed.item_code, sed.s_warehouse
		""", self.production_order, as_dict=1)

		backflushed_materials= {}
		for d in materials_already_backflushed:
			backflushed_materials.setdefault(d.item_code,[]).append({d.warehouse: d.qty})

		po_qty = frappe.db.sql("""select qty, produced_qty, material_transferred_for_manufacturing from
			`tabProduction Order` where name=%s""", self.production_order, as_dict=1)[0]
		manufacturing_qty = flt(po_qty.qty)
		produced_qty = flt(po_qty.produced_qty)
		trans_qty = flt(po_qty.material_transferred_for_manufacturing)

		for item in transferred_materials:
			qty= item.qty

			if trans_qty and manufacturing_qty > (produced_qty + flt(self.fg_completed_qty)):
				qty = (qty/trans_qty) * flt(self.fg_completed_qty)

			elif backflushed_materials.get(item.item_code):
				for d in backflushed_materials.get(item.item_code):
					if d.get(item.warehouse):
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
					}
				})

	def get_pending_raw_materials(self):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_dict = self.get_bom_raw_materials(1)
		issued_item_qty = self.get_issued_qty()

		max_qty = flt(self.pro_doc.qty)
		for item in item_dict:
			pending_to_issue = (max_qty * item_dict[item]["qty"]) - issued_item_qty.get(item, 0)
			desire_to_transfer = flt(self.fg_completed_qty) * item_dict[item]["qty"]

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
			frappe.msgprint(_("""All items have already been transferred for this Production Order."""))

		return item_dict

	def get_issued_qty(self):
		issued_item_qty = {}
		result = frappe.db.sql("""select t1.item_code, sum(t1.qty)
			from `tabStock Entry Detail` t1, `tabStock Entry` t2
			where t1.parent = t2.name and t2.production_order = %s and t2.docstatus = 1
			and t2.purpose = 'Material Transfer for Manufacture'
			group by t1.item_code""", self.production_order)
		for t in result:
			issued_item_qty[t[0]] = flt(t[1])

		return issued_item_qty

	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		expense_account, cost_center = frappe.db.get_values("Company", self.company, \
			["default_expense_account", "cost_center"])[0]

		for d in item_dict:
			se_child = self.append('items')
			se_child.s_warehouse = item_dict[d].get("from_warehouse")
			se_child.t_warehouse = item_dict[d].get("to_warehouse")
			se_child.item_code = cstr(d)
			se_child.item_name = item_dict[d]["item_name"]
			se_child.description = item_dict[d]["description"]
			se_child.uom = item_dict[d]["stock_uom"]
			se_child.stock_uom = item_dict[d]["stock_uom"]
			se_child.qty = flt(item_dict[d]["qty"])
			se_child.expense_account = item_dict[d]["expense_account"] or expense_account
			se_child.cost_center = item_dict[d]["cost_center"] or cost_center

			if se_child.s_warehouse==None:
				se_child.s_warehouse = self.from_warehouse
			if se_child.t_warehouse==None:
				se_child.t_warehouse = self.to_warehouse

			# in stock uom
			se_child.transfer_qty = flt(item_dict[d]["qty"])
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
		if self.purpose in ["Material Transfer for Manufacture", "Manufacture", "Repack", "Subcontract"]:
			for item in self.get("items"):
				if item.batch_no:
					expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
					if expiry_date:
						if getdate(self.posting_date) > getdate(expiry_date):
							frappe.throw(_("Batch {0} of Item {1} has expired.").format(item.batch_no, item.item_code))

@frappe.whitelist()
def get_production_order_details(production_order):
	production_order = frappe.get_doc("Production Order", production_order)
	pending_qty_to_produce = flt(production_order.qty) - flt(production_order.produced_qty)

	return {
		"from_bom": 1,
		"bom_no": production_order.bom_no,
		"use_multi_level_bom": production_order.use_multi_level_bom,
		"wip_warehouse": production_order.wip_warehouse,
		"fg_warehouse": production_order.fg_warehouse,
		"fg_completed_qty": pending_qty_to_produce,
		"additional_costs": get_additional_costs(production_order, fg_qty=pending_qty_to_produce)
	}

def get_additional_costs(production_order=None, bom_no=None, fg_qty=None):
	additional_costs = []
	operating_cost_per_unit = get_operating_cost_per_unit(production_order, bom_no)
	if operating_cost_per_unit:
		additional_costs.append({
			"description": "Operating Cost as per Production Order / BOM",
			"amount": operating_cost_per_unit * flt(fg_qty)
		})

	if production_order and production_order.additional_operating_cost and production_order.qty:
		additional_operating_cost_per_unit = \
			flt(production_order.additional_operating_cost) / flt(production_order.qty)

		additional_costs.append({
			"description": "Additional Operating Cost",
			"amount": additional_operating_cost_per_unit * flt(fg_qty)
		})

	return additional_costs

def get_operating_cost_per_unit(production_order=None, bom_no=None):
	operating_cost_per_unit = 0
	if production_order:
		if not bom_no:
			bom_no = production_order.bom_no

		for d in production_order.get("operations"):
			if flt(d.completed_qty):
				operating_cost_per_unit += flt(d.actual_operating_cost) / flt(d.completed_qty)
			elif production_order.qty:
				operating_cost_per_unit += flt(d.planned_operating_cost) / flt(production_order.qty)

	# Get operating cost from BOM if not found in production_order.
	if not operating_cost_per_unit and bom_no:
		bom = frappe.db.get_value("BOM", bom_no, ["operating_cost", "quantity"], as_dict=1)
		if bom.quantity:
			operating_cost_per_unit = flt(bom.operating_cost) / flt(bom.quantity)

	return operating_cost_per_unit

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
def get_warehouse_details(args):
	if isinstance(args, basestring):
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
