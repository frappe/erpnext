# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.defaults

from webnotes.utils import cstr, cint, flt, comma_or, nowdate
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _
from stock.utils import get_incoming_rate
from stock.stock_ledger import get_previous_sle
from controllers.queries import get_match_cond
import json


class NotUpdateStockError(webnotes.ValidationError): pass
class StockOverReturnError(webnotes.ValidationError): pass
class IncorrectValuationRateError(webnotes.ValidationError): pass
class DuplicateEntryForProductionOrderError(webnotes.ValidationError): pass
class StockOverProductionError(webnotes.ValidationError): pass
	
from controllers.stock_controller import StockController

class DocType(StockController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist
		self.fname = 'mtn_details' 
		
	def validate(self):
		self.validate_posting_time()
		self.validate_purpose()
		pro_obj = self.doc.production_order and \
			get_obj('Production Order', self.doc.production_order) or None

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
		self.set_total_amount()
		
	def on_submit(self):
		self.update_stock_ledger()

		from stock.doctype.serial_no.serial_no import update_serial_nos_after_submit
		update_serial_nos_after_submit(self, "mtn_details")
		self.update_production_order()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_stock_ledger()
		self.update_production_order()
		self.make_cancel_gl_entries()
		
	def validate_fiscal_year(self):
		import accounts.utils
		accounts.utils.validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year,
			self.meta.get_label("posting_date"))
		
	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer", 
			"Manufacture/Repack", "Subcontract", "Sales Return", "Purchase Return"]
		if self.doc.purpose not in valid_purposes:
			msgprint(_("Purpose must be one of ") + comma_or(valid_purposes),
				raise_exception=True)
		
	def validate_item(self):
		stock_items = self.get_stock_items()
		for item in self.doclist.get({"parentfield": "mtn_details"}):
			if item.item_code not in stock_items:
				msgprint(_("""Only Stock Items are allowed for Stock Entry"""),
					raise_exception=True)
		
	def validate_warehouse(self, pro_obj):
		"""perform various (sometimes conditional) validations on warehouse"""
		
		source_mandatory = ["Material Issue", "Material Transfer", "Purchase Return"]
		target_mandatory = ["Material Receipt", "Material Transfer", "Sales Return"]
		
		validate_for_manufacture_repack = any([d.bom_no for d in self.doclist.get(
			{"parentfield": "mtn_details"})])

		if self.doc.purpose in source_mandatory and self.doc.purpose not in target_mandatory:
			self.doc.to_warehouse = None
			for d in getlist(self.doclist, 'mtn_details'):
				d.t_warehouse = None
		elif self.doc.purpose in target_mandatory and self.doc.purpose not in source_mandatory:
			self.doc.from_warehouse = None
			for d in getlist(self.doclist, 'mtn_details'):
				d.s_warehouse = None

		for d in getlist(self.doclist, 'mtn_details'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.doc.from_warehouse
				d.t_warehouse = self.doc.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				msgprint(_("Atleast one warehouse is mandatory"), raise_exception=1)
			
			if self.doc.purpose in source_mandatory and not d.s_warehouse:
				msgprint(_("Row # ") + "%s: " % cint(d.idx)
					+ _("Source Warehouse") + _(" is mandatory"), raise_exception=1)
				
			if self.doc.purpose in target_mandatory and not d.t_warehouse:
				msgprint(_("Row # ") + "%s: " % cint(d.idx)
					+ _("Target Warehouse") + _(" is mandatory"), raise_exception=1)

			if self.doc.purpose == "Manufacture/Repack":
				if validate_for_manufacture_repack:
					if d.bom_no:
						d.s_warehouse = None
						
						if not d.t_warehouse:
							msgprint(_("Row # ") + "%s: " % cint(d.idx)
								+ _("Target Warehouse") + _(" is mandatory"), raise_exception=1)
						
						elif pro_obj and cstr(d.t_warehouse) != pro_obj.doc.fg_warehouse:
							msgprint(_("Row # ") + "%s: " % cint(d.idx)
								+ _("Target Warehouse") + _(" should be same as that in ")
								+ _("Production Order"), raise_exception=1)
					
					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							msgprint(_("Row # ") + "%s: " % cint(d.idx)
								+ _("Source Warehouse") + _(" is mandatory"), raise_exception=1)
			
			if cstr(d.s_warehouse) == cstr(d.t_warehouse):
				msgprint(_("Source and Target Warehouse cannot be same"), 
					raise_exception=1)
				
	def validate_production_order(self, pro_obj=None):
		if not pro_obj:
			if self.doc.production_order:
				pro_obj = get_obj('Production Order', self.doc.production_order)
			else:
				return
		
		if self.doc.purpose == "Manufacture/Repack":
			# check for double entry
			self.check_duplicate_entry_for_production_order()
		elif self.doc.purpose != "Material Transfer":
			self.doc.production_order = None
	
	def check_duplicate_entry_for_production_order(self):
		other_ste = [t[0] for t in webnotes.conn.get_values("Stock Entry",  {
			"production_order": self.doc.production_order,
			"purpose": self.doc.purpose,
			"docstatus": ["!=", 2],
			"name": ["!=", self.doc.name]
		}, "name")]
		
		if other_ste:
			production_item, qty = webnotes.conn.get_value("Production Order", 
				self.doc.production_order, ["production_item", "qty"])
			args = other_ste + [production_item]
			fg_qty_already_entered = webnotes.conn.sql("""select sum(actual_qty)
				from `tabStock Entry Detail` 
				where parent in (%s) 
					and item_code = %s 
					and ifnull(s_warehouse,'')='' """ % (", ".join(["%s" * len(other_ste)]), "%s"), args)[0][0]
			
			if fg_qty_already_entered >= qty:
				webnotes.throw(_("Stock Entries already created for Production Order ") 
					+ self.doc.production_order + ":" + ", ".join(other_ste), DuplicateEntryForProductionOrderError)

	def set_total_amount(self):
		self.doc.total_amount = sum([flt(item.amount) for item in self.doclist.get({"parentfield": "mtn_details"})])
			
	def get_stock_and_rate(self):
		"""get stock and incoming rate on posting date"""
		for d in getlist(self.doclist, 'mtn_details'):
			args = webnotes._dict({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"qty": d.s_warehouse and -1*d.transfer_qty or d.transfer_qty,
				"serial_no": d.serial_no,
				"bom_no": d.bom_no,
			})
			# get actual stock at source warehouse
			d.actual_qty = get_previous_sle(args).get("qty_after_transaction") or 0
			
			# get incoming rate
			if not flt(d.incoming_rate):
				d.incoming_rate = self.get_incoming_rate(args)
				
			d.amount = flt(d.transfer_qty) * flt(d.incoming_rate)
			
	def get_incoming_rate(self, args):
		incoming_rate = 0
		if self.doc.purpose == "Sales Return" and \
				(self.doc.delivery_note_no or self.doc.sales_invoice_no):
			sle = webnotes.conn.sql("""select name, posting_date, posting_time, 
				actual_qty, stock_value, warehouse from `tabStock Ledger Entry` 
				where voucher_type = %s and voucher_no = %s and 
				item_code = %s limit 1""", 
				((self.doc.delivery_note_no and "Delivery Note" or "Sales Invoice"),
				self.doc.delivery_note_no or self.doc.sales_invoice_no, args.item_code), as_dict=1)
			if sle:
				args.update({
					"posting_date": sle[0].posting_date,
					"posting_time": sle[0].posting_time,
					"sle": sle[0].name,
					"warehouse": sle[0].warehouse,
				})
				previous_sle = get_previous_sle(args)
				incoming_rate = (flt(sle[0].stock_value) - flt(previous_sle.get("stock_value"))) / \
					flt(sle[0].actual_qty)
		else:
			incoming_rate = get_incoming_rate(args)
			
		return incoming_rate
		
	def validate_incoming_rate(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if d.t_warehouse:
				self.validate_value("incoming_rate", ">", 0, d, raise_exception=IncorrectValuationRateError)
					
	def validate_bom(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if d.bom_no and not webnotes.conn.sql("""select name from `tabBOM`
					where item = %s and name = %s and docstatus = 1 and is_active = 1""",
					(d.item_code, d.bom_no)):
				msgprint(_("Item") + " %s: " % cstr(d.item_code)
					+ _("does not belong to BOM: ") + cstr(d.bom_no)
					+ _(" or the BOM is cancelled or inactive"), raise_exception=1)
					
	def validate_finished_goods(self):
		"""validation: finished good quantity should be same as manufacturing quantity"""
		for d in getlist(self.doclist, 'mtn_details'):
			if d.bom_no and flt(d.transfer_qty) != flt(self.doc.fg_completed_qty):
				msgprint(_("Row #") + " %s: " % d.idx 
					+ _("Quantity should be equal to Manufacturing Quantity. ")
					+ _("To fetch items again, click on 'Get Items' button \
						or update the Quantity manually."), raise_exception=1)
						
	def validate_return_reference_doc(self):
		"""validate item with reference doc"""
		ref = get_return_doclist_and_details(self.doc.fields)
		
		if ref.doclist:
			# validate docstatus
			if ref.doclist[0].docstatus != 1:
				webnotes.msgprint(_(ref.doclist[0].doctype) + ' "' + ref.doclist[0].name + '": ' 
					+ _("Status should be Submitted"), raise_exception=webnotes.InvalidStatusError)
			
			# update stock check
			if ref.doclist[0].doctype == "Sales Invoice" and cint(ref.doclist[0].update_stock) != 1:
				webnotes.msgprint(_(ref.doclist[0].doctype) + ' "' + ref.doclist[0].name + '": ' 
					+ _("Update Stock should be checked."), 
					raise_exception=NotUpdateStockError)
			
			# posting date check
			ref_posting_datetime = "%s %s" % (cstr(ref.doclist[0].posting_date), 
				cstr(ref.doclist[0].posting_time) or "00:00:00")
			this_posting_datetime = "%s %s" % (cstr(self.doc.posting_date), 
				cstr(self.doc.posting_time))
			if this_posting_datetime < ref_posting_datetime:
				from webnotes.utils.dateutils import datetime_in_user_format
				webnotes.msgprint(_("Posting Date Time cannot be before")
					+ ": " + datetime_in_user_format(ref_posting_datetime),
					raise_exception=True)
			
			stock_items = get_stock_items_for_return(ref.doclist, ref.parentfields)
			already_returned_item_qty = self.get_already_returned_item_qty(ref.fieldname)
			
			for item in self.doclist.get({"parentfield": "mtn_details"}):
				# validate if item exists in the ref doclist and that it is a stock item
				if item.item_code not in stock_items:
					msgprint(_("Item") + ': "' + item.item_code + _("\" does not exist in ") +
						ref.doclist[0].doctype + ": " + ref.doclist[0].name, 
						raise_exception=webnotes.DoesNotExistError)
				
				# validate quantity <= ref item's qty - qty already returned
				ref_item = ref.doclist.getone({"item_code": item.item_code})
				returnable_qty = ref_item.qty - flt(already_returned_item_qty.get(item.item_code))
				if not returnable_qty:
					webnotes.throw("{item}: {item_code} {returned}".format(
						item=_("Item"), item_code=item.item_code, 
						returned=_("already returned though some other documents")), 
						StockOverReturnError)
				elif item.transfer_qty > returnable_qty:
					webnotes.throw("{item}: {item_code}, {returned}: {qty}".format(
						item=_("Item"), item_code=item.item_code,
						returned=_("Max Returnable Qty"), qty=returnable_qty), StockOverReturnError)
						
	def get_already_returned_item_qty(self, ref_fieldname):
		return dict(webnotes.conn.sql("""select item_code, sum(transfer_qty) as qty
			from `tabStock Entry Detail` where parent in (
				select name from `tabStock Entry` where `%s`=%s and docstatus=1)
			group by item_code""" % (ref_fieldname, "%s"), (self.doc.fields.get(ref_fieldname),)))
						
	def update_stock_ledger(self):
		sl_entries = []			
		for d in getlist(self.doclist, 'mtn_details'):
			if cstr(d.s_warehouse) and self.doc.docstatus == 1:
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
			
			if cstr(d.s_warehouse) and self.doc.docstatus == 2:
				sl_entries.append(self.get_sl_entries(d, {
					"warehouse": cstr(d.s_warehouse),
					"actual_qty": -flt(d.transfer_qty),
					"incoming_rate": 0
				}))
				
		self.make_sl_entries(sl_entries, self.doc.amended_from and 'Yes' or 'No')

	def update_production_order(self):
		def _validate_production_order(pro_bean):
			if flt(pro_bean.doc.docstatus) != 1:
				webnotes.throw(_("Production Order must be submitted") + ": " + 
					self.doc.production_order)
					
			if pro_bean.doc.status == 'Stopped':
				msgprint(_("Transaction not allowed against stopped Production Order") + ": " + 
					self.doc.production_order)
		
		if self.doc.production_order:
			pro_bean = webnotes.bean("Production Order", self.doc.production_order)
			_validate_production_order(pro_bean)
			self.update_produced_qty(pro_bean)
			if self.doc.purpose == "Manufacture/Repack":
				self.update_planned_qty(pro_bean)
			
	def update_produced_qty(self, pro_bean):
		if self.doc.purpose == "Manufacture/Repack":
			produced_qty = flt(pro_bean.doc.produced_qty) + \
				(self.doc.docstatus==1 and 1 or -1 ) * flt(self.doc.fg_completed_qty)
				
			if produced_qty > flt(pro_bean.doc.qty):
				webnotes.throw(_("Production Order") + ": " + self.doc.production_order + "\n" +
					_("Total Manufactured Qty can not be greater than Planned qty to manufacture") 
					+ "(%s/%s)" % (produced_qty, flt(pro_bean.doc.qty)), StockOverProductionError)
					
			status = 'Completed' if flt(produced_qty) >= flt(pro_bean.doc.qty) else 'In Process'
			webnotes.conn.sql("""update `tabProduction Order` set status=%s, produced_qty=%s 
				where name=%s""", (status, produced_qty, self.doc.production_order))
			
	def update_planned_qty(self, pro_bean):
		from stock.utils import update_bin
		update_bin({
			"item_code": pro_bean.doc.production_item,
			"warehouse": pro_bean.doc.fg_warehouse,
			"posting_date": self.doc.posting_date,
			"planned_qty": (self.doc.docstatus==1 and -1 or 1 ) * flt(self.doc.fg_completed_qty)
		})
					
	def get_item_details(self, arg):
		arg = json.loads(arg)
		item = webnotes.conn.sql("""select stock_uom, description, item_name, 
			purchase_account, cost_center from `tabItem` 
			where name = %s and (ifnull(end_of_life,'')='' or end_of_life ='0000-00-00' 
			or end_of_life > now())""", (arg.get('item_code')), as_dict = 1)
		if not item: 
			msgprint("Item is not active", raise_exception=1)
						
		ret = {
			'uom'			      	: item and item[0]['stock_uom'] or '',
			'stock_uom'			  	: item and item[0]['stock_uom'] or '',
			'description'		  	: item and item[0]['description'] or '',
			'item_name' 		  	: item and item[0]['item_name'] or '',
			'expense_account'		: item and item[0]['purchase_account'] or arg.get("expense_account") \
				or webnotes.conn.get_value("Company", arg.get("company"), "default_expense_account"),
			'cost_center'			: item and item[0]['cost_center'] or arg.get("cost_center"),
			'qty'					: 0,
			'transfer_qty'			: 0,
			'conversion_factor'		: 1,
     		'batch_no'          	: '',
			'actual_qty'			: 0,
			'incoming_rate'			: 0
		}
		stock_and_rate = arg.get('warehouse') and self.get_warehouse_details(json.dumps(arg)) or {}
		ret.update(stock_and_rate)
		return ret

	def get_uom_details(self, arg = ''):
		arg, ret = eval(arg), {}
		uom = webnotes.conn.sql("""select conversion_factor from `tabUOM Conversion Detail` 
			where parent = %s and uom = %s""", (arg['item_code'], arg['uom']), as_dict = 1)
		if not uom or not flt(uom[0].conversion_factor):
			msgprint("There is no Conversion Factor for UOM '%s' in Item '%s'" % (arg['uom'],
				arg['item_code']))
			ret = {'uom' : ''}
		else:
			ret = {
				'conversion_factor'		: flt(uom[0]['conversion_factor']),
				'transfer_qty'			: flt(arg['qty']) * flt(uom[0]['conversion_factor']),
			}
		return ret
		
	def get_warehouse_details(self, args):
		args = json.loads(args)
		ret = {}
		if args.get('warehouse') and args.get('item_code'):
			args.update({
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
			})
			args = webnotes._dict(args)
		
			ret = {
				"actual_qty" : get_previous_sle(args).get("qty_after_transaction") or 0,
				"incoming_rate" : self.get_incoming_rate(args)
			}
		return ret
		
	def get_items(self):
		self.doclist = filter(lambda d: d.parentfield!="mtn_details", self.doclist)
		# self.doclist = self.doc.clear_table(self.doclist, 'mtn_details')
		
		pro_obj = None
		if self.doc.production_order:
			# common validations
			pro_obj = get_obj('Production Order', self.doc.production_order)
			if pro_obj:
				self.validate_production_order(pro_obj)
				self.doc.bom_no = pro_obj.doc.bom_no
			else:
				# invalid production order
				self.doc.production_order = None
		
		if self.doc.bom_no:
			if self.doc.purpose in ["Material Issue", "Material Transfer", "Manufacture/Repack",
					"Subcontract"]:
				if self.doc.production_order and self.doc.purpose == "Material Transfer":
					item_dict = self.get_pending_raw_materials(pro_obj)
				else:
					if not self.doc.fg_completed_qty:
						webnotes.throw(_("Manufacturing Quantity is mandatory"))
					item_dict = self.get_bom_raw_materials(self.doc.fg_completed_qty)
					for item in item_dict.values():
						if pro_obj:
							item["from_warehouse"] = pro_obj.doc.wip_warehouse
						item["to_warehouse"] = ""

				# add raw materials to Stock Entry Detail table
				idx = self.add_to_stock_entry_detail(item_dict)
					
			# add finished good item to Stock Entry Detail table -- along with bom_no
			if self.doc.production_order and self.doc.purpose == "Manufacture/Repack":
				item = webnotes.conn.get_value("Item", pro_obj.doc.production_item, ["item_name", 
					"description", "stock_uom", "purchase_account", "cost_center"], as_dict=1)
				self.add_to_stock_entry_detail({
					cstr(pro_obj.doc.production_item): {
						"to_warehouse": pro_obj.doc.fg_warehouse,
						"from_warehouse": "",
						"qty": self.doc.fg_completed_qty,
						"item_name": item.item_name,
						"description": item.description,
						"stock_uom": item.stock_uom,
						"expense_account": item.purchase_account,
						"cost_center": item.cost_center,
					}
				}, bom_no=pro_obj.doc.bom_no, idx=idx)
								
			elif self.doc.purpose in ["Material Receipt", "Manufacture/Repack"]:
				if self.doc.purpose=="Material Receipt":
					self.doc.from_warehouse = ""
					
				item = webnotes.conn.sql("""select name, item_name, description, 
					stock_uom, purchase_account, cost_center from `tabItem` 
					where name=(select item from tabBOM where name=%s)""", 
					self.doc.bom_no, as_dict=1)
				self.add_to_stock_entry_detail({
					item[0]["name"] : {
						"qty": self.doc.fg_completed_qty,
						"item_name": item[0].item_name,
						"description": item[0]["description"],
						"stock_uom": item[0]["stock_uom"],
						"from_warehouse": "",
						"expense_account": item[0].purchase_account,
						"cost_center": item[0].cost_center,
					}
				}, bom_no=self.doc.bom_no, idx=idx)
		
		self.get_stock_and_rate()
	
	def get_bom_raw_materials(self, qty):
		from manufacturing.doctype.bom.bom import get_bom_items_as_dict
		
		# item dict = { item_code: {qty, description, stock_uom} }
		item_dict = get_bom_items_as_dict(self.doc.bom_no, qty=qty, fetch_exploded = self.doc.use_multi_level_bom)
		
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
		
		max_qty = flt(pro_obj.doc.qty)
		only_pending_fetched = []
		
		for item in item_dict:
			pending_to_issue = (max_qty * item_dict[item]["qty"]) - issued_item_qty.get(item, 0)
			desire_to_transfer = flt(self.doc.fg_completed_qty) * item_dict[item]["qty"]
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
			webnotes.msgprint(_("""All items have already been transferred \
				for this Production Order."""))
			
		elif only_pending_fetched:
			webnotes.msgprint(_("""Only quantities pending to be transferred \
				were fetched for the following items:\n""" + "\n".join(only_pending_fetched)))

		return item_dict

	def get_issued_qty(self):
		issued_item_qty = {}
		result = webnotes.conn.sql("""select t1.item_code, sum(t1.qty)
			from `tabStock Entry Detail` t1, `tabStock Entry` t2
			where t1.parent = t2.name and t2.production_order = %s and t2.docstatus = 1
			and t2.purpose = 'Material Transfer'
			group by t1.item_code""", self.doc.production_order)
		for t in result:
			issued_item_qty[t[0]] = flt(t[1])
		
		return issued_item_qty

	def add_to_stock_entry_detail(self, item_dict, bom_no=None, idx=None):
		if not idx:	idx = 1
		expense_account, cost_center = webnotes.conn.get_values("Company", self.doc.company, \
			["default_expense_account", "cost_center"])[0]

		for d in item_dict:
			se_child = addchild(self.doc, 'mtn_details', 'Stock Entry Detail', 
				self.doclist)
			se_child.idx = idx
			se_child.s_warehouse = item_dict[d].get("from_warehouse", self.doc.from_warehouse)
			se_child.t_warehouse = item_dict[d].get("to_warehouse", self.doc.to_warehouse)
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

			# increment idx by 1
			idx += 1
		return idx

	def get_cust_values(self):
		"""fetches customer details"""
		if self.doc.delivery_note_no:
			doctype = "Delivery Note"
			name = self.doc.delivery_note_no
		else:
			doctype = "Sales Invoice"
			name = self.doc.sales_invoice_no
		
		result = webnotes.conn.sql("""select customer, customer_name,
			address_display as customer_address
			from `tab%s` where name=%s""" % (doctype, "%s"), (name,), as_dict=1)
		
		return result and result[0] or {}
		
	def get_cust_addr(self):
		from utilities.transaction_base import get_default_address, get_address_display
		res = webnotes.conn.sql("select customer_name from `tabCustomer` where name = '%s'"%self.doc.customer)
		address_display = None
		customer_address = get_default_address("customer", self.doc.customer)
		if customer_address:
			address_display = get_address_display(customer_address)
		ret = { 
			'customer_name'		: res and res[0][0] or '',
			'customer_address' : address_display}

		return ret

	def get_supp_values(self):
		result = webnotes.conn.sql("""select supplier, supplier_name,
			address_display as supplier_address
			from `tabPurchase Receipt` where name=%s""", (self.doc.purchase_receipt_no,),
			as_dict=1)
		
		return result and result[0] or {}
		
	def get_supp_addr(self):
		from utilities.transaction_base import get_default_address, get_address_display
		res = webnotes.conn.sql("""select supplier_name from `tabSupplier`
			where name=%s""", self.doc.supplier)
		address_display = None
		supplier_address = get_default_address("customer", self.doc.customer)
		if supplier_address:
			address_display = get_address_display(supplier_address)	
		
		ret = {
			'supplier_name' : res and res[0][0] or '',
			'supplier_address' : address_display }
		return ret
		
	def validate_with_material_request(self):
		for item in self.doclist.get({"parentfield": "mtn_details"}):
			if item.material_request:
				mreq_item = webnotes.conn.get_value("Material Request Item", 
					{"name": item.material_request_item, "parent": item.material_request},
					["item_code", "warehouse", "idx"], as_dict=True)
				if mreq_item.item_code != item.item_code or mreq_item.warehouse != item.t_warehouse:
					msgprint(_("Row #") + (" %d: " % item.idx) + _("does not match")
						+ " " + _("Row #") + (" %d %s " % (mreq_item.idx, _("of")))
						+ _("Material Request") + (" - %s" % item.material_request), 
						raise_exception=webnotes.MappingMismatchError)
	
@webnotes.whitelist()
def get_production_order_details(production_order):
	result = webnotes.conn.sql("""select bom_no, 
		ifnull(qty, 0) - ifnull(produced_qty, 0) as fg_completed_qty, use_multi_level_bom, 
		wip_warehouse from `tabProduction Order` where name = %s""", production_order, as_dict=1)
	return result and result[0] or {}
	
def query_sales_return_doc(doctype, txt, searchfield, start, page_len, filters):
	conditions = ""
	if doctype == "Sales Invoice":
		conditions = "and update_stock=1"
	
	return webnotes.conn.sql("""select name, customer, customer_name
		from `tab%s` where docstatus = 1
			and (`%s` like %%(txt)s 
				or `customer` like %%(txt)s) %s %s
		order by name, customer, customer_name
		limit %s""" % (doctype, searchfield, conditions, 
		get_match_cond(doctype, searchfield), "%(start)s, %(page_len)s"), 
		{"txt": "%%%s%%" % txt, "start": start, "page_len": page_len}, 
		as_list=True)
	
def query_purchase_return_doc(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, supplier, supplier_name
		from `tab%s` where docstatus = 1
			and (`%s` like %%(txt)s 
				or `supplier` like %%(txt)s) %s
		order by name, supplier, supplier_name
		limit %s""" % (doctype, searchfield, get_match_cond(doctype, searchfield), 
		"%(start)s, %(page_len)s"),	{"txt": "%%%s%%" % txt, "start": 
		start, "page_len": page_len}, as_list=True)
		
def query_return_item(doctype, txt, searchfield, start, page_len, filters):
	txt = txt.replace("%", "")

	ref = get_return_doclist_and_details(filters)
			
	stock_items = get_stock_items_for_return(ref.doclist, ref.parentfields)
	
	result = []
	for item in ref.doclist.get({"parentfield": ["in", ref.parentfields]}):
		if item.item_code in stock_items:
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
		'item_code': filters['item_code'], 
		's_warehouse': filters['s_warehouse'], 
		'posting_date': filters['posting_date'], 
		'txt': "%%%s%%" % txt, 
		'mcond':get_match_cond(doctype, searchfield), 
		"start": start, 
		"page_len": page_len
	}
	
	if filters.get("s_warehouse"):
		batch_nos = webnotes.conn.sql("""select batch_no 
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
		return webnotes.conn.sql("""select name from `tabBatch` 
			where item = '%(item_code)s'
			and docstatus < 2
			and (ifnull(expiry_date, '2099-12-31') >= %(posting_date)s 
				or expiry_date = '' or expiry_date = "0000-00-00")
			%(mcond)s
			order by name desc 
			limit %(start)s, %(page_len)s
		""" % args)

def get_stock_items_for_return(ref_doclist, parentfields):
	"""return item codes filtered from doclist, which are stock items"""
	if isinstance(parentfields, basestring):
		parentfields = [parentfields]
	
	all_items = list(set([d.item_code for d in 
		ref_doclist.get({"parentfield": ["in", parentfields]})]))
	stock_items = webnotes.conn.sql_list("""select name from `tabItem`
		where is_stock_item='Yes' and name in (%s)""" % (", ".join(["%s"] * len(all_items))),
		tuple(all_items))

	return stock_items
	
def get_return_doclist_and_details(args):
	ref = webnotes._dict()
	
	# get ref_doclist
	if args["purpose"] in return_map:
		for fieldname, val in return_map[args["purpose"]].items():
			if args.get(fieldname):
				ref.fieldname = fieldname
				ref.doclist = webnotes.get_doclist(val[0], args[fieldname])
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

@webnotes.whitelist()
def make_return_jv(stock_entry):
	se = webnotes.bean("Stock Entry", stock_entry)
	if not se.doc.purpose in ["Sales Return", "Purchase Return"]:
		return
	
	ref = get_return_doclist_and_details(se.doc.fields)
	
	if ref.doclist[0].doctype == "Delivery Note":
		result = make_return_jv_from_delivery_note(se, ref)
	elif ref.doclist[0].doctype == "Sales Invoice":
		result = make_return_jv_from_sales_invoice(se, ref)
	elif ref.doclist[0].doctype == "Purchase Receipt":
		result = make_return_jv_from_purchase_receipt(se, ref)
	
	# create jv doclist and fetch balance for each unique row item
	jv_list = [{
		"__islocal": 1,
		"doctype": "Journal Voucher",
		"posting_date": se.doc.posting_date,
		"voucher_type": se.doc.purpose == "Sales Return" and "Credit Note" or "Debit Note",
		"fiscal_year": se.doc.fiscal_year,
		"company": se.doc.company
	}]
	
	from accounts.utils import get_balance_on
	for r in result:
		jv_list.append({
			"__islocal": 1,
			"doctype": "Journal Voucher Detail",
			"parentfield": "entries",
			"account": r.get("account"),
			"against_invoice": r.get("against_invoice"),
			"against_voucher": r.get("against_voucher"),
			"balance": get_balance_on(r.get("account"), se.doc.posting_date) \
				if r.get("account") else 0
		})
		
	return jv_list
	
def make_return_jv_from_sales_invoice(se, ref):
	# customer account entry
	parent = {
		"account": ref.doclist[0].debit_to,
		"against_invoice": ref.doclist[0].name,
	}
	
	# income account entries
	children = []
	for se_item in se.doclist.get({"parentfield": "mtn_details"}):
		# find item in ref.doclist
		ref_item = ref.doclist.getone({"item_code": se_item.item_code})
		
		account = get_sales_account_from_item(ref.doclist, ref_item)
		
		if account not in children:
			children.append(account)
			
	return [parent] + [{"account": account} for account in children]
	
def get_sales_account_from_item(doclist, ref_item):
	account = None
	if not ref_item.income_account:
		if ref_item.parent_item:
			parent_item = doclist.getone({"item_code": ref_item.parent_item})
			account = parent_item.income_account
	else:
		account = ref_item.income_account
	
	return account
	
def make_return_jv_from_delivery_note(se, ref):
	invoices_against_delivery = get_invoice_list("Sales Invoice Item", "delivery_note",
		ref.doclist[0].name)
	
	if not invoices_against_delivery:
		sales_orders_against_delivery = [d.against_sales_order for d in ref.doclist if d.against_sales_order]
		
		if sales_orders_against_delivery:
			invoices_against_delivery = get_invoice_list("Sales Invoice Item", "sales_order",
				sales_orders_against_delivery)
			
	if not invoices_against_delivery:
		return []
		
	packing_item_parent_map = dict([[d.item_code, d.parent_item] for d in ref.doclist.get(
		{"parentfield": ref.parentfields[1]})])
	
	parent = {}
	children = []
	
	for se_item in se.doclist.get({"parentfield": "mtn_details"}):
		for sales_invoice in invoices_against_delivery:
			si = webnotes.bean("Sales Invoice", sales_invoice)
			
			if se_item.item_code in packing_item_parent_map:
				ref_item = si.doclist.get({"item_code": packing_item_parent_map[se_item.item_code]})
			else:
				ref_item = si.doclist.get({"item_code": se_item.item_code})
			
			if not ref_item:
				continue
				
			ref_item = ref_item[0]
			
			account = get_sales_account_from_item(si.doclist, ref_item)
			
			if account not in children:
				children.append(account)
			
			if not parent:
				parent = {"account": si.doc.debit_to}

			break
			
	if len(invoices_against_delivery) == 1:
		parent["against_invoice"] = invoices_against_delivery[0]
	
	result = [parent] + [{"account": account} for account in children]
	
	return result
	
def get_invoice_list(doctype, link_field, value):
	if isinstance(value, basestring):
		value = [value]
	
	return webnotes.conn.sql_list("""select distinct parent from `tab%s`
		where docstatus = 1 and `%s` in (%s)""" % (doctype, link_field,
			", ".join(["%s"]*len(value))), tuple(value))
			
def make_return_jv_from_purchase_receipt(se, ref):
	invoice_against_receipt = get_invoice_list("Purchase Invoice Item", "purchase_receipt",
		ref.doclist[0].name)
	
	if not invoice_against_receipt:
		purchase_orders_against_receipt = [d.prevdoc_docname for d in 
			ref.doclist.get({"prevdoc_doctype": "Purchase Order"}) if d.prevdoc_docname]
		
		if purchase_orders_against_receipt:
			invoice_against_receipt = get_invoice_list("Purchase Invoice Item", "purchase_order",
				purchase_orders_against_receipt)
			
	if not invoice_against_receipt:
		return []
	
	parent = {}
	children = []
	
	for se_item in se.doclist.get({"parentfield": "mtn_details"}):
		for purchase_invoice in invoice_against_receipt:
			pi = webnotes.bean("Purchase Invoice", purchase_invoice)
			ref_item = pi.doclist.get({"item_code": se_item.item_code})
			
			if not ref_item:
				continue
				
			ref_item = ref_item[0]
			
			account = ref_item.expense_head
			
			if account not in children:
				children.append(account)
			
			if not parent:
				parent = {"account": pi.doc.credit_to}

			break
			
	if len(invoice_against_receipt) == 1:
		parent["against_voucher"] = invoice_against_receipt[0]
	
	result = [parent] + [{"account": account} for account in children]
	
	return result
		
