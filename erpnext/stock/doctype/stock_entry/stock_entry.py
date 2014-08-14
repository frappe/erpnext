# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults

from frappe.utils import cstr, cint, flt, comma_or, nowdate

from frappe import _
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.controllers.queries import get_match_cond
from erpnext.stock.get_item_details import get_available_qty

class NotUpdateStockError(frappe.ValidationError): pass
class StockOverReturnError(frappe.ValidationError): pass
class IncorrectValuationRateError(frappe.ValidationError): pass
class DuplicateEntryForProductionOrderError(frappe.ValidationError): pass

from erpnext.controllers.stock_controller import StockController

form_grid_templates = {
	"mtn_details": "templates/form_grid/stock_entry_grid.html"
}

class StockEntry(StockController):
	fname = 'mtn_details'
	def onload(self):
		if self.docstatus==1:
			for item in self.get(self.fname):
				item.update(get_available_qty(item.item_code,
					item.s_warehouse))

	def validate(self):
		self.validate_posting_time()
		self.validate_purpose()
		pro_obj = self.production_order and \
			frappe.get_doc('Production Order', self.production_order) or None

		self.set_transfer_qty()
		self.validate_item()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_uom_is_integer("stock_uom", "transfer_qty")
		self.validate_warehouse(pro_obj)
		self.validate_production_order(pro_obj)
		self.get_stock_and_rate()
		self.validate_incoming_rate()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_return_reference_doc()
		self.validate_with_material_request()
		self.validate_fiscal_year()
		self.validate_valuation_rate()
		self.set_total_amount()

	def on_submit(self):
		self.update_stock_ledger()

		from erpnext.stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "mtn_details")
		self.update_production_order()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_production_order()
		self.make_gl_entries_on_cancel()

	def validate_fiscal_year(self):
		from erpnext.accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.posting_date, self.fiscal_year,
			self.meta.get_label("posting_date"))

	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer",
			"Manufacture/Repack", "Subcontract", "Sales Return", "Purchase Return"]
		if self.purpose not in valid_purposes:
			frappe.throw(_("Purpose must be one of {0}").format(comma_or(valid_purposes)))

	def set_transfer_qty(self):
		for item in self.get("mtn_details"):
			if not flt(item.qty):
				frappe.throw(_("Row {0}: Qty is mandatory").format(item.idx))

			item.transfer_qty = flt(item.qty * item.conversion_factor, self.precision("transfer_qty", item))

	def validate_item(self):
		stock_items = self.get_stock_items()
		serialized_items = self.get_serialized_items()
		for item in self.get("mtn_details"):
			if item.item_code not in stock_items:
				frappe.throw(_("{0} is not a stock Item").format(item.item_code))
			if not item.stock_uom:
				item.stock_uom = frappe.db.get_value("Item", item.item_code, "stock_uom")
			if not item.uom:
				item.uom = item.stock_uom
			if not item.conversion_factor:
				item.conversion_factor = 1
			if not item.transfer_qty:
				item.transfer_qty = item.qty * item.conversion_factor
			if (self.purpose in ("Material Transfer", "Sales Return", "Purchase Return")
				and not item.serial_no
				and item.item_code in serialized_items):
				frappe.throw(_("Row #{0}: Please specify Serial No for Item {1}").format(item.idx, item.item_code),
					frappe.MandatoryError)


	def validate_warehouse(self, pro_obj):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = ["Material Issue", "Material Transfer", "Purchase Return"]
		target_mandatory = ["Material Receipt", "Material Transfer", "Sales Return"]

		validate_for_manufacture_repack = any([d.bom_no for d in self.get("mtn_details")])

		if self.purpose in source_mandatory and self.purpose not in target_mandatory:
			self.to_warehouse = None
			for d in self.get('mtn_details'):
				d.t_warehouse = None
		elif self.purpose in target_mandatory and self.purpose not in source_mandatory:
			self.from_warehouse = None
			for d in self.get('mtn_details'):
				d.s_warehouse = None

		for d in self.get('mtn_details'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.from_warehouse
				d.t_warehouse = self.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				frappe.throw(_("Atleast one warehouse is mandatory"))

			if self.purpose in source_mandatory and not d.s_warehouse:
				frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose in target_mandatory and not d.t_warehouse:
				frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose == "Manufacture/Repack":
				if validate_for_manufacture_repack:
					if d.bom_no:
						d.s_warehouse = None

						if not d.t_warehouse:
							frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

						elif pro_obj and cstr(d.t_warehouse) != pro_obj.fg_warehouse:
							frappe.throw(_("Target warehouse in row {0} must be same as Production Order").format(d.idx))

					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse):
				frappe.throw(_("Source and target warehouse cannot be same for row {0}").format(d.idx))

	def validate_production_order(self, pro_obj=None):
		if not pro_obj:
			if self.production_order:
				pro_obj = frappe.get_doc('Production Order', self.production_order)
			else:
				return

		if self.purpose == "Manufacture/Repack":
			# check for double entry
			self.check_duplicate_entry_for_production_order()
		elif self.purpose != "Material Transfer":
			self.production_order = None

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
		if self.purpose == "Manufacture/Repack":
			valuation_at_source, valuation_at_target = 0, 0
			for d in self.get("mtn_details"):
				if d.s_warehouse and not d.t_warehouse:
					valuation_at_source += flt(d.amount)
				if d.t_warehouse and not d.s_warehouse:
					valuation_at_target += flt(d.amount)

			if valuation_at_target < valuation_at_source:
				frappe.throw(_("Total valuation for manufactured or repacked item(s) can not be less than total valuation of raw materials"))

	def set_total_amount(self):
		self.total_amount = sum([flt(item.amount) for item in self.get("mtn_details")])

	def get_stock_and_rate(self):
		"""get stock and incoming rate on posting date"""

		raw_material_cost = 0.0

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		allow_negative_stock = cint(frappe.db.get_default("allow_negative_stock"))

		for d in self.get('mtn_details'):
			args = frappe._dict({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"qty": d.s_warehouse and -1*d.transfer_qty or d.transfer_qty,
				"serial_no": d.serial_no
			})

			# get actual stock at source warehouse
			d.actual_qty = get_previous_sle(args).get("qty_after_transaction") or 0

			# validate qty during submit
			if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and d.actual_qty < d.transfer_qty:
				frappe.throw(_("""Row {0}: Qty not avalable in warehouse {1} on {2} {3}.
					Available Qty: {4}, Transfer Qty: {5}""").format(d.idx, d.s_warehouse,
					self.posting_date, self.posting_time, d.actual_qty, d.transfer_qty))

			# get incoming rate
			if not d.bom_no:
				if not flt(d.incoming_rate) or d.s_warehouse or self.purpose == "Sales Return":
					incoming_rate = flt(self.get_incoming_rate(args), self.precision("incoming_rate", d))
					if incoming_rate > 0:
						d.incoming_rate = incoming_rate

				d.amount = flt(d.transfer_qty) * flt(d.incoming_rate)
				raw_material_cost += flt(d.amount)

		# set incoming rate for fg item
		if self.purpose == "Manufacture/Repack":
			for d in self.get("mtn_details"):
				if d.bom_no:
					if not flt(d.incoming_rate):
						bom = frappe.db.get_value("BOM", d.bom_no, ["operating_cost", "quantity"], as_dict=1)
						operation_cost_per_unit = flt(bom.operating_cost) / flt(bom.quantity)
						d.incoming_rate = operation_cost_per_unit + (raw_material_cost / flt(d.transfer_qty))
					d.amount = flt(d.transfer_qty) * flt(d.incoming_rate)

	def get_incoming_rate(self, args):
		incoming_rate = 0
		if self.purpose == "Sales Return":
			incoming_rate = self.get_incoming_rate_for_sales_return(args)
		else:
			incoming_rate = get_incoming_rate(args)

		return incoming_rate

	def get_incoming_rate_for_sales_return(self, args):
		incoming_rate = 0.0
		if (self.delivery_note_no or self.sales_invoice_no) and args.get("item_code"):
			incoming_rate = frappe.db.sql("""select abs(ifnull(stock_value_difference, 0) / actual_qty)
				from `tabStock Ledger Entry`
				where voucher_type = %s and voucher_no = %s and item_code = %s limit 1""",
				((self.delivery_note_no and "Delivery Note" or "Sales Invoice"),
				self.delivery_note_no or self.sales_invoice_no, args.item_code))
			incoming_rate = incoming_rate[0][0] if incoming_rate else 0.0

		return incoming_rate

	def validate_incoming_rate(self):
		for d in self.get('mtn_details'):
			if d.t_warehouse:
				self.validate_value("incoming_rate", ">", 0, d, raise_exception=IncorrectValuationRateError)

	def validate_bom(self):
		for d in self.get('mtn_details'):
			if d.bom_no and not frappe.db.sql("""select name from `tabBOM`
					where item = %s and name = %s and docstatus = 1 and is_active = 1""",
					(d.item_code, d.bom_no)):
				frappe.throw(_("BOM {0} is not submitted or inactive BOM for Item {1}").format(d.bom_no, d.item_code))

	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		for d in self.get('mtn_details'):
			if d.bom_no and flt(d.transfer_qty) != flt(self.fg_completed_qty):
				frappe.throw(_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}").format(d.idx, d.transfer_qty, self.fg_completed_qty))

	def validate_return_reference_doc(self):
		"""validate item with reference doc"""
		ref = get_return_doc_and_details(self)

		if ref.doc:
			# validate docstatus
			if ref.doc.docstatus != 1:
				frappe.throw(_("{0} {1} must be submitted").format(ref.doc.doctype, ref.doc.name),
					frappe.InvalidStatusError)

			# update stock check
			if ref.doc.doctype == "Sales Invoice" and cint(ref.doc.update_stock) != 1:
				frappe.throw(_("'Update Stock' for Sales Invoice {0} must be set").format(ref.doc.name), NotUpdateStockError)

			# posting date check
			ref_posting_datetime = "%s %s" % (cstr(ref.doc.posting_date),
				cstr(ref.doc.posting_time) or "00:00:00")
			this_posting_datetime = "%s %s" % (cstr(self.posting_date),
				cstr(self.posting_time))
			if this_posting_datetime < ref_posting_datetime:
				from frappe.utils.dateutils import datetime_in_user_format
				frappe.throw(_("Posting timestamp must be after {0}").format(datetime_in_user_format(ref_posting_datetime)))

			stock_items = get_stock_items_for_return(ref.doc, ref.parentfields)
			already_returned_item_qty = self.get_already_returned_item_qty(ref.fieldname)

			for item in self.get("mtn_details"):
				# validate if item exists in the ref doc and that it is a stock item
				if item.item_code not in stock_items:
					frappe.throw(_("Item {0} does not exist in {1} {2}").format(item.item_code, ref.doc.doctype, ref.doc.name),
						frappe.DoesNotExistError)

				# validate quantity <= ref item's qty - qty already returned
				if self.purpose == "Purchase Return":
					ref_item_qty = sum([flt(d.qty)*flt(d.conversion_factor) for d in ref.doc.get({"item_code": item.item_code})])
				elif self.purpose == "Sales Return":
					ref_item_qty = sum([flt(d.qty) for d in ref.doc.get({"item_code": item.item_code})])
				returnable_qty = ref_item_qty - flt(already_returned_item_qty.get(item.item_code))
				if not returnable_qty:
					frappe.throw(_("Item {0} has already been returned").format(item.item_code), StockOverReturnError)
				elif item.transfer_qty > returnable_qty:
					frappe.throw(_("Cannot return more than {0} for Item {1}").format(returnable_qty, item.item_code),
						StockOverReturnError)

	def get_already_returned_item_qty(self, ref_fieldname):
		return dict(frappe.db.sql("""select item_code, sum(transfer_qty) as qty
			from `tabStock Entry Detail` where parent in (
				select name from `tabStock Entry` where `%s`=%s and docstatus=1)
			group by item_code""" % (ref_fieldname, "%s"), (self.get(ref_fieldname),)))

	def update_stock_ledger(self):
		sl_entries = []
		for d in self.get('mtn_details'):
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
			if self.purpose == "Manufacture/Repack":
				pro_doc.run_method("update_produced_qty")
				self.update_planned_qty(pro_doc)

	def update_planned_qty(self, pro_doc):
		from erpnext.stock.utils import update_bin
		update_bin({
			"item_code": pro_doc.production_item,
			"warehouse": pro_doc.fg_warehouse,
			"posting_date": self.posting_date,
			"planned_qty": (self.docstatus==1 and -1 or 1 ) * flt(self.fg_completed_qty)
		})

	def get_item_details(self, args):
		item = frappe.db.sql("""select stock_uom, description, item_name,
			expense_account, buying_cost_center from `tabItem`
			where name = %s and (ifnull(end_of_life,'0000-00-00')='0000-00-00' or end_of_life > now())""",
			(args.get('item_code')), as_dict = 1)
		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		ret = {
			'uom'			      	: item and item[0]['stock_uom'] or '',
			'stock_uom'			  	: item and item[0]['stock_uom'] or '',
			'description'		  	: item and item[0]['description'] or '',
			'item_name' 		  	: item and item[0]['item_name'] or '',
			'expense_account'		: args.get("expense_account") \
				or frappe.db.get_value("Company", args.get("company"), "stock_adjustment_account"),
			'cost_center'			: item and item[0]['buying_cost_center'] or args.get("cost_center"),
			'qty'					: 0,
			'transfer_qty'			: 0,
			'conversion_factor'		: 1,
     		'batch_no'          	: '',
			'actual_qty'			: 0,
			'incoming_rate'			: 0
		}
		stock_and_rate = args.get('warehouse') and self.get_warehouse_details(args) or {}
		ret.update(stock_and_rate)
		return ret

	def get_uom_details(self, args):
		conversion_factor = frappe.db.get_value("UOM Conversion Detail", {"parent": args.get("item_code"),
			"uom": args.get("uom")}, "conversion_factor")

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
				"incoming_rate" : self.get_incoming_rate(args)
			}
		return ret

	def get_items(self):
		self.set('mtn_details', [])

		pro_obj = None
		if self.production_order:
			# common validations
			pro_obj = frappe.get_doc('Production Order', self.production_order)
			if pro_obj:
				self.validate_production_order(pro_obj)
				self.bom_no = pro_obj.bom_no
			else:
				# invalid production order
				self.production_order = None

		if self.bom_no:
			if self.purpose in ["Material Issue", "Material Transfer", "Manufacture/Repack",
					"Subcontract"]:
				if self.production_order and self.purpose == "Material Transfer":
					item_dict = self.get_pending_raw_materials(pro_obj)
				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))
					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)
					for item in item_dict.values():
						if pro_obj:
							item["from_warehouse"] = pro_obj.wip_warehouse
						item["to_warehouse"] = ""

				# add raw materials to Stock Entry Detail table
				self.add_to_stock_entry_detail(item_dict)

			# add finished good item to Stock Entry Detail table -- along with bom_no
			if self.production_order and self.purpose == "Manufacture/Repack":
				item = frappe.db.get_value("Item", pro_obj.production_item, ["item_name",
					"description", "stock_uom", "expense_account", "buying_cost_center"], as_dict=1)
				self.add_to_stock_entry_detail({
					cstr(pro_obj.production_item): {
						"to_warehouse": pro_obj.fg_warehouse,
						"from_warehouse": "",
						"qty": self.fg_completed_qty,
						"item_name": item.item_name,
						"description": item.description,
						"stock_uom": item.stock_uom,
						"expense_account": item.expense_account,
						"cost_center": item.buying_cost_center,
					}
				}, bom_no=pro_obj.bom_no)

			elif self.purpose in ["Material Receipt", "Manufacture/Repack"]:
				if self.purpose=="Material Receipt":
					self.from_warehouse = ""

				item = frappe.db.sql("""select name, item_name, description,
					stock_uom, expense_account, buying_cost_center from `tabItem`
					where name=(select item from tabBOM where name=%s)""",
					self.bom_no, as_dict=1)
				self.add_to_stock_entry_detail({
					item[0]["name"] : {
						"qty": self.fg_completed_qty,
						"item_name": item[0].item_name,
						"description": item[0]["description"],
						"stock_uom": item[0]["stock_uom"],
						"from_warehouse": "",
						"expense_account": item[0].expense_account,
						"cost_center": item[0].buying_cost_center,
					}
				}, bom_no=self.bom_no)

		self.get_stock_and_rate()

	def get_bom_raw_materials(self, qty):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.bom_no, qty=qty, fetch_exploded = self.use_multi_level_bom)

		for item in item_dict.values():
			item.from_warehouse = item.default_warehouse

		return item_dict

	def get_pending_raw_materials(self, pro_obj):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_dict = self.get_bom_raw_materials(1)
		issued_item_qty = self.get_issued_qty()

		max_qty = flt(pro_obj.qty)
		only_pending_fetched = []

		for item in item_dict:
			pending_to_issue = (max_qty * item_dict[item]["qty"]) - issued_item_qty.get(item, 0)
			desire_to_transfer = flt(self.fg_completed_qty) * item_dict[item]["qty"]
			if desire_to_transfer <= pending_to_issue:
				item_dict[item]["qty"] = desire_to_transfer
			else:
				item_dict[item]["qty"] = pending_to_issue
				if pending_to_issue:
					only_pending_fetched.append(item)

		# delete items with 0 qty
		for item in item_dict.keys():
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Production Order."""))

		elif only_pending_fetched:
			frappe.msgprint(_("Pending Items {0} updated").format(only_pending_fetched))

		return item_dict

	def get_issued_qty(self):
		issued_item_qty = {}
		result = frappe.db.sql("""select t1.item_code, sum(t1.qty)
			from `tabStock Entry Detail` t1, `tabStock Entry` t2
			where t1.parent = t2.name and t2.production_order = %s and t2.docstatus = 1
			and t2.purpose = 'Material Transfer'
			group by t1.item_code""", self.production_order)
		for t in result:
			issued_item_qty[t[0]] = flt(t[1])

		return issued_item_qty

	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		expense_account, cost_center = frappe.db.get_values("Company", self.company, \
			["default_expense_account", "cost_center"])[0]

		for d in item_dict:
			se_child = self.append('mtn_details')
			se_child.s_warehouse = item_dict[d].get("from_warehouse", self.from_warehouse)
			se_child.t_warehouse = item_dict[d].get("to_warehouse", self.to_warehouse)
			se_child.item_code = cstr(d)
			se_child.item_name = item_dict[d]["item_name"]
			se_child.description = item_dict[d]["description"]
			se_child.uom = item_dict[d]["stock_uom"]
			se_child.stock_uom = item_dict[d]["stock_uom"]
			se_child.qty = flt(item_dict[d]["qty"])
			se_child.expense_account = item_dict[d]["expense_account"] or expense_account
			se_child.cost_center = item_dict[d]["cost_center"] or cost_center

			# in stock uom
			se_child.transfer_qty = flt(item_dict[d]["qty"])
			se_child.conversion_factor = 1.00

			# to be assigned for finished item
			se_child.bom_no = bom_no

	def validate_with_material_request(self):
		for item in self.get("mtn_details"):
			if item.material_request:
				mreq_item = frappe.db.get_value("Material Request Item",
					{"name": item.material_request_item, "parent": item.material_request},
					["item_code", "warehouse", "idx"], as_dict=True)
				if mreq_item.item_code != item.item_code or mreq_item.warehouse != item.t_warehouse:
					frappe.throw(_("Item or Warehouse for row {0} does not match Material Request").format(item.idx),
						frappe.MappingMismatchError)

@frappe.whitelist()
def get_party_details(ref_dt, ref_dn):
	if ref_dt in ["Delivery Note", "Sales Invoice"]:
		res = frappe.db.get_value(ref_dt, ref_dn,
			["customer", "customer_name", "address_display as customer_address"], as_dict=1)
	else:
		res = frappe.db.get_value(ref_dt, ref_dn,
			["supplier", "supplier_name", "address_display as supplier_address"], as_dict=1)
	return res or {}

@frappe.whitelist()
def get_production_order_details(production_order):
	result = frappe.db.sql("""select bom_no,
		ifnull(qty, 0) - ifnull(produced_qty, 0) as fg_completed_qty, use_multi_level_bom,
		wip_warehouse from `tabProduction Order` where name = %s""", production_order, as_dict=1)
	return result and result[0] or {}

def query_sales_return_doc(doctype, txt, searchfield, start, page_len, filters):
	conditions = ""
	if doctype == "Sales Invoice":
		conditions = "and update_stock=1"

	return frappe.db.sql("""select name, customer, customer_name
		from `tab%s` where docstatus = 1
			and (`%s` like %%(txt)s
				or `customer` like %%(txt)s) %s %s
		order by name, customer, customer_name
		limit %s""" % (doctype, searchfield, conditions,
		get_match_cond(doctype), "%(start)s, %(page_len)s"),
		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len},
		as_list=True)

def query_purchase_return_doc(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name, supplier, supplier_name
		from `tab%s` where docstatus = 1
			and (`%s` like %%(txt)s
				or `supplier` like %%(txt)s) %s
		order by name, supplier, supplier_name
		limit %s""" % (doctype, searchfield, get_match_cond(doctype),
		"%(start)s, %(page_len)s"),	{"txt": "%%%s%%" % txt, "start":
		start, "page_len": page_len}, as_list=True)

def query_return_item(doctype, txt, searchfield, start, page_len, filters):
	txt = txt.replace("%", "")

	ref = get_return_doc_and_details(filters)

	stock_items = get_stock_items_for_return(ref.doc, ref.parentfields)

	result = []
	for item in ref.doc.get_all_children():
		if getattr(item, "item_code", None) in stock_items:
			item.item_name = cstr(item.item_name)
			item.description = cstr(item.description)
			if (txt in item.item_code) or (txt in item.item_name) or (txt in item.description):
				val = [
					item.item_code,
					(len(item.item_name) > 40) and (item.item_name[:40] + "...") or item.item_name,
					(len(item.description) > 40) and (item.description[:40] + "...") or \
						item.description
				]
				if val not in result:
					result.append(val)

	return result[start:start+page_len]

def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("posting_date"):
		filters["posting_date"] = nowdate()

	batch_nos = None
	args = {
		'item_code': filters.get("item_code"),
		's_warehouse': filters.get('s_warehouse'),
		'posting_date': filters.get('posting_date'),
		'txt': "%%%s%%" % txt,
		'mcond':get_match_cond(doctype),
		"start": start,
		"page_len": page_len
	}

	if filters.get("s_warehouse"):
		batch_nos = frappe.db.sql("""select batch_no
			from `tabStock Ledger Entry` sle
			where item_code = '%(item_code)s'
				and warehouse = '%(s_warehouse)s'
				and batch_no like '%(txt)s'
				and exists(select * from `tabBatch`
					where name = sle.batch_no
					and (ifnull(expiry_date, '2099-12-31') >= %(posting_date)s
						or expiry_date = '')
					and docstatus != 2)
			%(mcond)s
			group by batch_no having sum(actual_qty) > 0
			order by batch_no desc
			limit %(start)s, %(page_len)s """
			% args)

	if batch_nos:
		return batch_nos
	else:
		return frappe.db.sql("""select name from `tabBatch`
			where item = '%(item_code)s'
			and docstatus < 2
			and (ifnull(expiry_date, '2099-12-31') >= %(posting_date)s
				or expiry_date = '' or expiry_date = "0000-00-00")
			%(mcond)s
			order by name desc
			limit %(start)s, %(page_len)s
		""" % args)

def get_stock_items_for_return(ref_doc, parentfields):
	"""return item codes filtered from doc, which are stock items"""
	if isinstance(parentfields, basestring):
		parentfields = [parentfields]

	all_items = list(set([d.item_code for d in
		ref_doc.get_all_children() if d.get("item_code")]))
	stock_items = frappe.db.sql_list("""select name from `tabItem`
		where is_stock_item='Yes' and name in (%s)""" % (", ".join(["%s"] * len(all_items))),
		tuple(all_items))

	return stock_items

def get_return_doc_and_details(args):
	ref = frappe._dict()

	# get ref_doc
	if args.get("purpose") in return_map:
		for fieldname, val in return_map[args.get("purpose")].items():
			if args.get(fieldname):
				ref.fieldname = fieldname
				ref.doc = frappe.get_doc(val[0], args.get(fieldname))
				ref.parentfields = val[1]
				break

	return ref

return_map = {
	"Sales Return": {
		# [Ref DocType, [Item tables' parentfields]]
		"delivery_note_no": ["Delivery Note", ["delivery_note_details", "packing_details"]],
		"sales_invoice_no": ["Sales Invoice", ["entries", "packing_details"]]
	},
	"Purchase Return": {
		"purchase_receipt_no": ["Purchase Receipt", ["purchase_receipt_details"]]
	}
}

@frappe.whitelist()
def make_return_jv(stock_entry):
	se = frappe.get_doc("Stock Entry", stock_entry)
	if not se.purpose in ["Sales Return", "Purchase Return"]:
		return

	ref = get_return_doc_and_details(se)

	if ref.doc.doctype == "Delivery Note":
		result = make_return_jv_from_delivery_note(se, ref)
	elif ref.doc.doctype == "Sales Invoice":
		result = make_return_jv_from_sales_invoice(se, ref)
	elif ref.doc.doctype == "Purchase Receipt":
		result = make_return_jv_from_purchase_receipt(se, ref)

	# create jv doc and fetch balance for each unique row item
	jv = frappe.new_doc("Journal Voucher")
	jv.update({
		"posting_date": se.posting_date,
		"voucher_type": se.purpose == "Sales Return" and "Credit Note" or "Debit Note",
		"fiscal_year": se.fiscal_year,
		"company": se.company
	})

	from erpnext.accounts.utils import get_balance_on
	for r in result:
		jv.append("entries", {
			"account": r.get("account"),
			"against_invoice": r.get("against_invoice"),
			"against_voucher": r.get("against_voucher"),
			"balance": get_balance_on(r.get("account"), se.posting_date) if r.get("account") else 0
		})

	return jv

def make_return_jv_from_sales_invoice(se, ref):
	# customer account entry
	parent = {
		"account": ref.doc.debit_to,
		"against_invoice": ref.doc.name,
	}

	# income account entries
	children = []
	for se_item in se.get("mtn_details"):
		# find item in ref.doc
		ref_item = ref.doc.get({"item_code": se_item.item_code})[0]

		account = get_sales_account_from_item(ref.doc, ref_item)

		if account not in children:
			children.append(account)

	return [parent] + [{"account": account} for account in children]

def get_sales_account_from_item(doc, ref_item):
	account = None
	if not getattr(ref_item, "income_account", None):
		if ref_item.parent_item:
			parent_item = doc.get(doc.fname, {"item_code": ref_item.parent_item})[0]
			account = parent_item.income_account
	else:
		account = ref_item.income_account

	return account

def make_return_jv_from_delivery_note(se, ref):
	invoices_against_delivery = get_invoice_list("Sales Invoice Item", "delivery_note",
		ref.doc.name)

	if not invoices_against_delivery:
		sales_orders_against_delivery = [d.against_sales_order for d in ref.doc.get_all_children() if getattr(d, "against_sales_order", None)]

		if sales_orders_against_delivery:
			invoices_against_delivery = get_invoice_list("Sales Invoice Item", "sales_order",
				sales_orders_against_delivery)

	if not invoices_against_delivery:
		return []

	packing_item_parent_map = dict([[d.item_code, d.parent_item] for d in ref.doc.get(ref.parentfields[1])])

	parent = {}
	children = []

	for se_item in se.get("mtn_details"):
		for sales_invoice in invoices_against_delivery:
			si = frappe.get_doc("Sales Invoice", sales_invoice)

			if se_item.item_code in packing_item_parent_map:
				ref_item = si.get({"item_code": packing_item_parent_map[se_item.item_code]})
			else:
				ref_item = si.get({"item_code": se_item.item_code})

			if not ref_item:
				continue

			ref_item = ref_item[0]

			account = get_sales_account_from_item(si, ref_item)

			if account not in children:
				children.append(account)

			if not parent:
				parent = {"account": si.debit_to}

			break

	if len(invoices_against_delivery) == 1:
		parent["against_invoice"] = invoices_against_delivery[0]

	result = [parent] + [{"account": account} for account in children]

	return result

def get_invoice_list(doctype, link_field, value):
	if isinstance(value, basestring):
		value = [value]

	return frappe.db.sql_list("""select distinct parent from `tab%s`
		where docstatus = 1 and `%s` in (%s)""" % (doctype, link_field,
			", ".join(["%s"]*len(value))), tuple(value))

def make_return_jv_from_purchase_receipt(se, ref):
	invoice_against_receipt = get_invoice_list("Purchase Invoice Item", "purchase_receipt",
		ref.doc.name)

	if not invoice_against_receipt:
		purchase_orders_against_receipt = [d.prevdoc_docname for d in
			ref.doc.get(ref.doc.fname, {"prevdoc_doctype": "Purchase Order"})
			if getattr(d, "prevdoc_docname", None)]

		if purchase_orders_against_receipt:
			invoice_against_receipt = get_invoice_list("Purchase Invoice Item", "purchase_order",
				purchase_orders_against_receipt)

	if not invoice_against_receipt:
		return []

	parent = {}
	children = []

	for se_item in se.get("mtn_details"):
		for purchase_invoice in invoice_against_receipt:
			pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
			ref_item = pi.get({"item_code": se_item.item_code})

			if not ref_item:
				continue

			ref_item = ref_item[0]

			account = ref_item.expense_account

			if account not in children:
				children.append(account)

			if not parent:
				parent = {"account": pi.credit_to}

			break

	if len(invoice_against_receipt) == 1:
		parent["against_voucher"] = invoice_against_receipt[0]

	result = [parent] + [{"account": account} for account in children]

	return result
