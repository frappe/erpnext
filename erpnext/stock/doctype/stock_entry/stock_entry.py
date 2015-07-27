# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import _
from frappe.utils import cstr, cint, flt, comma_or, get_datetime, getdate
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError
from erpnext.controllers.queries import get_match_cond
from erpnext.stock.get_item_details import get_available_qty, get_default_cost_center, get_conversion_factor
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no
from erpnext.accounts.utils import validate_fiscal_year

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
		if self.docstatus==1:
			for item in self.get("items"):
				item.update(get_available_qty(item.item_code,
					item.s_warehouse))

	def validate(self):
		self.pro_doc = None
		if self.production_order:
			self.pro_doc = frappe.get_doc('Production Order', self.production_order)

		self.validate_posting_time()
		self.validate_purpose()
		validate_fiscal_year(self.posting_date, self.fiscal_year, self.meta.get_label("posting_date"), self)
		self.validate_item()
		self.set_transfer_qty()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse()
		self.validate_production_order()
		self.get_stock_and_rate()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_with_material_request()
		self.validate_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()
		self.validate_batch()

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

		if self.purpose in ("Manufacture", "Repack") and not self.difference_account:
			self.difference_account = frappe.db.get_value("Company", self.company, "default_expense_account")

	def set_transfer_qty(self):
		for item in self.get("items"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx))

			item.transfer_qty = flt(item.qty * item.conversion_factor, self.precision("transfer_qty", item))

	def validate_item(self):
		stock_items = self.get_stock_items()
		serialized_items = self.get_serialized_items()
		for item in self.get("items"):
			if item.item_code not in stock_items:
				frappe.throw(_("{0} is not a stock Item").format(item.item_code))

			item_details = self.get_item_details(frappe._dict({"item_code": item.item_code,
				"company": self.company, "project_name": self.project_name}))

			for f in ("uom", "stock_uom", "description", "item_name", "expense_account",
				"cost_center", "conversion_factor"):
					if f in ["stock_uom", "conversion_factor"] or not item.get(f):
						item.set(f, item_details.get(f))

			if self.difference_account:
				item.expense_account = self.difference_account

			if not item.transfer_qty:
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

						elif self.pro_doc and cstr(d.t_warehouse) != self.pro_doc.fg_warehouse:
							frappe.throw(_("Target warehouse in row {0} must be same as Production Order").format(d.idx))

					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse):
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

	def validate_production_order(self):
		if self.purpose in ("Manufacture", "Material Transfer for Manufacture"):
			# check if production order is entered
			if not self.production_order:
				frappe.throw(_("Production order number is mandatory for stock entry purpose manufacture"))
			# check for double entry
			if self.purpose=="Manufacture":
				if not self.fg_completed_qty:
					frappe.throw(_("For Quantity (Manufactured Qty) is mandatory"))
				self.check_if_operations_completed()
				self.check_duplicate_entry_for_production_order()
		elif self.purpose != "Material Transfer":
			self.production_order = None

	def check_if_operations_completed(self):
		"""Check if Time Logs are completed against before manufacturing to capture operating costs."""
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

	def validate_valuation_rate(self):
		if self.purpose in ["Manufacture", "Repack"]:
			valuation_at_source, valuation_at_target = 0, 0
			for d in self.get("items"):
				if d.s_warehouse and not d.t_warehouse:
					valuation_at_source += flt(d.amount)
				if d.t_warehouse and not d.s_warehouse:
					valuation_at_target += flt(d.amount)

			if valuation_at_target + 0.001 < valuation_at_source:
				frappe.throw(_("Total valuation ({0}) for manufactured or repacked item(s) can not be less than total valuation of raw materials ({1})").format(valuation_at_target,
					valuation_at_source))

	def set_total_incoming_outgoing_value(self):
		self.total_incoming_value = self.total_outgoing_value = 0.0
		for d in self.get("items"):
			if d.s_warehouse:
				self.total_incoming_value += flt(d.amount)
			if d.t_warehouse:
				self.total_outgoing_value += flt(d.amount)

		self.value_difference = self.total_outgoing_value - self.total_incoming_value

	def set_total_amount(self):
		self.total_amount = sum([flt(item.amount) for item in self.get("items")])

	def get_stock_and_rate(self, force=False):
		"""get stock and incoming rate on posting date"""

		raw_material_cost = 0.0

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock"))

		for d in self.get('items'):
			d.transfer_qty = flt(d.transfer_qty)

			args = frappe._dict({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": d.s_warehouse and -1*d.transfer_qty or d.transfer_qty,
				"serial_no": d.serial_no,
			})

			# get actual stock at source warehouse
			d.actual_qty = get_previous_sle(args).get("qty_after_transaction") or 0

			# validate qty during submit
			if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and d.actual_qty < d.transfer_qty:
				frappe.throw(_("""Row {0}: Qty not avalable in warehouse {1} on {2} {3}.
					Available Qty: {4}, Transfer Qty: {5}""").format(d.idx, d.s_warehouse,
					self.posting_date, self.posting_time, d.actual_qty, d.transfer_qty), NegativeStockError)

			# get incoming rate
			if not d.bom_no:
				if not flt(d.incoming_rate) or d.s_warehouse or force:
					incoming_rate = flt(get_incoming_rate(args), self.precision("incoming_rate", d))
					if incoming_rate > 0:
						d.incoming_rate = incoming_rate

				d.amount = flt(flt(d.transfer_qty) * flt(d.incoming_rate), d.precision("amount"))
				if not d.t_warehouse:
					raw_material_cost += flt(d.amount)


		self.add_operation_cost(raw_material_cost, force)

	def add_operation_cost(self, raw_material_cost, force):
		"""Adds operating cost if Production Order is set"""
		# set incoming rate for fg item
		if self.purpose in ["Manufacture", "Repack"]:
			number_of_fg_items = len([t.t_warehouse for t in self.get("items") if t.t_warehouse])
			for d in self.get("items"):
				if d.bom_no or (d.t_warehouse and number_of_fg_items == 1):
					operation_cost_per_unit = self.get_operation_cost_per_unit(d.bom_no, d.qty)

					d.incoming_rate = operation_cost_per_unit + (raw_material_cost / flt(d.transfer_qty))
					d.amount = flt(flt(d.transfer_qty) * flt(d.incoming_rate), self.precision("transfer_qty", d))
					break

	def get_operation_cost_per_unit(self, bom_no, qty):
		"""Returns operating cost from Production Order for given `bom_no`"""
		operation_cost_per_unit = 0

		if self.production_order:
			if not getattr(self, "pro_doc", None):
				self.pro_doc = frappe.get_doc("Production Order", self.production_order)
			for d in self.pro_doc.get("operations"):
				if flt(d.completed_qty):
					operation_cost_per_unit += flt(d.actual_operating_cost) / flt(d.completed_qty)
				else:
					operation_cost_per_unit += flt(d.planned_operating_cost) / flt(self.pro_doc.qty)

		# set operating cost from BOM if specified.
		if not operation_cost_per_unit and bom_no:
			bom = frappe.db.get_value("BOM", bom_no, ["operating_cost", "quantity"], as_dict=1)
			operation_cost_per_unit = flt(bom.operating_cost) / flt(bom.quantity)

		return operation_cost_per_unit + (flt(self.additional_operating_cost) / flt(qty))

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
			if d.bom_no:
				validate_bom_no(d.item_code, d.bom_no)

	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		items_with_target_warehouse = []
		for d in self.get('items'):
			if d.bom_no and flt(d.transfer_qty) != flt(self.fg_completed_qty):
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
		for d in self.get('items'):
			if cstr(d.s_warehouse) and self.docstatus == 1:
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.s_warehouse),
					"actual_qty": -flt(d.transfer_qty),
					"incoming_rate": 0
				}))

			if cstr(d.t_warehouse):
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.t_warehouse),
					"actual_qty": flt(d.transfer_qty),
					"incoming_rate": flt(d.incoming_rate)
				}))

			# On cancellation, make stock ledger entry for
			# target warehouse first, to update serial no values properly

			if cstr(d.s_warehouse) and self.docstatus == 2:
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.s_warehouse),
					"actual_qty": -flt(d.transfer_qty),
					"incoming_rate": 0
				}))

		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')

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
					self.update_planned_qty(pro_doc)

	def update_planned_qty(self, pro_doc):
		from erpnext.stock.utils import update_bin
		update_bin({
			"item_code": pro_doc.production_item,
			"warehouse": pro_doc.fg_warehouse,
			"posting_date": self.posting_date,
			"planned_qty": (self.docstatus==1 and -1 or 1 ) * flt(self.fg_completed_qty)
		})

	def get_item_details(self, args=None):
		item = frappe.db.sql("""select stock_uom, description, image, item_name,
			expense_account, buying_cost_center, item_group from `tabItem`
			where name = %s and (ifnull(end_of_life,'0000-00-00')='0000-00-00' or end_of_life > now())""",
			(args.get('item_code')), as_dict = 1)
		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))
			
		item = item[0]

		ret = {
			'uom'			      	: item.stock_uom,
			'stock_uom'			  	: item.stock_uom,
			'description'		  	: item.description,
			'image'					: item.image,
			'item_name' 		  	: item.item_name,
			'expense_account'		: args.get("expense_account") \
				or frappe.db.get_value("Company", args.get("company"), "stock_adjustment_account"),
			'cost_center'			: get_default_cost_center(args, item),
			'qty'					: 0,
			'transfer_qty'			: 0,
			'conversion_factor'		: 1,
			'batch_no'				: '',
			'actual_qty'			: 0,
			'incoming_rate'			: 0
		}
		stock_and_rate = args.get('warehouse') and self.get_warehouse_details(args) or {}
		ret.update(stock_and_rate)
		return ret

	def get_uom_details(self, args):
		conversion_factor = get_conversion_factor(args.get("item_code"), args.get("uom")).get("conversion_factor")

		if not conversion_factor:
			frappe.msgprint(_("UOM coversion factor required for UOM: {0} in Item: {1}")
				.format(args.get("uom"), args.get("item_code")))
			ret = {'uom' : ''}
		else:
			ret = {
				'conversion_factor'		: flt(conversion_factor),
				'transfer_qty'			: flt(args.get("qty")) * flt(conversion_factor)
			}
		return ret

	def get_warehouse_details(self, args):
		ret = {}
		if args.get('warehouse') and args.get('item_code'):
			args.update({
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
			})
			args = frappe._dict(args)

			ret = {
				"actual_qty" : get_previous_sle(args).get("qty_after_transaction") or 0,
				"incoming_rate" : get_incoming_rate(args)
			}
		return ret

	def get_items(self):
		self.set('items', [])
		self.validate_production_order()

		if not getattr(self, "pro_doc", None):
			self.pro_doc = None

		if self.production_order:
			# common validations
			if not self.pro_doc:
				self.pro_doc = frappe.get_doc('Production Order', self.production_order)

			if self.pro_doc:
				self.bom_no = self.pro_doc.bom_no
			else:
				# invalid production order
				self.production_order = None

		if self.bom_no:
			if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
					"Subcontract", "Material Transfer for Manufacture"]:
				if self.production_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials()
					if self.to_warehouse and self.pro_doc:
						for item in item_dict.values():
							item["to_warehouse"] = self.pro_doc.wip_warehouse
				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)
					for item in item_dict.values():
						if self.pro_doc:
							item["from_warehouse"] = self.pro_doc.wip_warehouse

						item["to_warehouse"] = self.to_warehouse if self.purpose=="Subcontract" else ""

				# add raw materials to Stock Entry Detail table
				self.add_to_stock_entry_detail(item_dict)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.load_items_from_bom()

		self.get_stock_and_rate()

	def load_items_from_bom(self):
		if self.production_order:
			item_code = self.pro_doc.production_item
			to_warehouse = self.pro_doc.fg_warehouse
		else:
			item_code = frappe.db.get_value("BOM", self.bom_no, "item")
			to_warehouse = ""

		item = frappe.db.get_value("Item", item_code, ["item_name",
			"description", "stock_uom", "expense_account", "buying_cost_center", "name"], as_dict=1)

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
		item_dict = get_bom_items_as_dict(self.bom_no, qty=qty, fetch_exploded = self.use_multi_level_bom)

		for item in item_dict.values():
			item.from_warehouse = self.from_warehouse or item.default_warehouse

		return item_dict

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
	res = frappe.db.sql("""select bom_no, use_multi_level_bom, wip_warehouse,
		ifnull(qty, 0) - ifnull(produced_qty, 0) as fg_completed_qty,
		(ifnull(additional_operating_cost, 0) / qty)*(ifnull(qty, 0) - ifnull(produced_qty, 0)) as additional_operating_cost
		from `tabProduction Order` where name = %s""", production_order, as_dict=1)

	return res and res[0] or {}
