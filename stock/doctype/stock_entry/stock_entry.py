# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, cint, flt, comma_or
from webnotes.model.doc import Document, addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _
from stock.utils import get_incoming_rate
from stock.stock_ledger import get_previous_sle
import json


sql = webnotes.conn.sql
	
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.fname = 'mtn_details' 
		
	def validate(self):
		self.validate_purpose()

		self.validate_serial_nos()
		pro_obj = self.doc.production_order and \
			get_obj('Production Order', self.doc.production_order) or None

		self.validate_warehouse(pro_obj)
		self.validate_production_order(pro_obj)
		self.get_stock_and_rate()
		self.validate_incoming_rate()
		self.validate_bom()
		self.validate_finished_goods()
		self.validate_return_reference_doc()
		
		self.validate_with_material_request()
		
	def on_submit(self):
		self.update_serial_no(1)
		self.update_stock_ledger(0)
		# update Production Order
		self.update_production_order(1)

	def on_cancel(self):
		self.update_serial_no(0)
		self.update_stock_ledger(1)
		# update Production Order
		self.update_production_order(0)
		
	def validate_purpose(self):
		valid_purposes = ["Material Issue", "Material Receipt", "Material Transfer", 
			"Manufacture/Repack", "Subcontract", "Sales Return", "Purchase Return"]
		if self.doc.purpose not in valid_purposes:
			msgprint(_("Purpose must be one of ") + comma_or(valid_purposes),
				raise_exception=True)
					
	def validate_serial_nos(self):
		sl_obj = get_obj("Stock Ledger")
		sl_obj.scrub_serial_nos(self)
		sl_obj.validate_serial_no(self, 'mtn_details')
		
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
			if not flt(self.doc.fg_completed_qty):
				msgprint(_("Manufacturing Quantity") + _(" is mandatory"), raise_exception=1)
			
			if flt(pro_obj.doc.qty) < (flt(pro_obj.doc.produced_qty)
					+ flt(self.doc.fg_completed_qty)):
				# do not allow manufacture of qty > production order qty
				msgprint(_("For Item ") + pro_obj.doc.production_item 
					+ _("Quantity already manufactured")
					+ " = %s." % flt(pro_obj.doc.produced_qty)
					+ _("Hence, maximum allowed Manufacturing Quantity")
					+ " = %s." % (flt(pro_obj.doc.qty) - flt(pro_obj.doc.produced_qty)),
					raise_exception=1)
		elif self.doc.purpose != "Material Transfer":
			self.doc.production_order = None
			
	def get_stock_and_rate(self):
		"""get stock and incoming rate on posting date"""
		for d in getlist(self.doclist, 'mtn_details'):
			args = webnotes._dict({
				"item_code": d.item_code,
				"warehouse": d.s_warehouse or d.t_warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time,
				"qty": d.s_warehouse and -1*d.transfer_qty or d.transfer_qty,
				"serial_no": cstr(d.serial_no).strip(),
				"bom_no": d.bom_no,
			})
			# get actual stock at source warehouse
			d.actual_qty = get_previous_sle(args).get("qty_after_transaction") or 0
			
			# get incoming rate
			if not flt(d.incoming_rate):
				d.incoming_rate = self.get_incoming_rate(args)
				
			d.amount = flt(d.qty) * flt(d.incoming_rate)
			
	def get_incoming_rate(self, args):
		incoming_rate = 0
		if self.doc.purpose == "Sales Return" and \
				(self.doc.delivery_note_no or self.doc.sales_invoice_no):
			sle = webnotes.conn.sql("""select name, posting_date, posting_time, 
				actual_qty, stock_value, warehouse from `tabStock Ledger Entry` 
				where voucher_type = %s and voucher_no = %s and 
				item_code = %s and ifnull(is_cancelled, 'No') = 'No' limit 1""", 
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
			if not flt(d.incoming_rate) and d.t_warehouse:
				msgprint("Rate is mandatory for Item: %s at row %s" % (d.item_code, d.idx),
					raise_exception=1)
					
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
		""" validate item with reference doc"""
		ref_doctype = ref_docname = ""
		if self.doc.purpose == "Sales Return" and \
				(self.doc.delivery_note_no or self.doc.sales_invoice_no):
			ref_doctype = self.doc.delivery_note_no and "Delivery Note" or "Sales Invoice"
			ref_docname = self.doc.delivery_note_no or self.doc.sales_invoice_no
		elif self.doc.purpose == "Purchase Return" and self.doc.purchase_receipt_no:
			ref_doctype = "Purchase Receipt"
			ref_docname = self.doc.purchase_receipt_no
			
		if ref_doctype and ref_docname:
			for item in self.doclist.get({"parentfield": "mtn_details"}):
				ref_exists = webnotes.conn.sql("""select name from `tab%s` 
					where parent = %s and item_code = %s and docstatus=1""" % 
					(ref_doctype + " Item", '%s', '%s'), (ref_docname, item.item_code))
					
				if not ref_exists:
					msgprint(_("Item: '") + item.item_code + _("' does not exists in ") +
						ref_doctype + ": " + ref_docname, raise_exception=1)
			
	def update_serial_no(self, is_submit):
		"""Create / Update Serial No"""
		from stock.utils import get_valid_serial_nos
		
		sl_obj = get_obj('Stock Ledger')
		if is_submit:
			sl_obj.validate_serial_no_warehouse(self, 'mtn_details')
		
		for d in getlist(self.doclist, 'mtn_details'):
			if cstr(d.serial_no).strip():
				for x in get_valid_serial_nos(d.serial_no):
					serial_no = x.strip()
					if d.s_warehouse:
						sl_obj.update_serial_delivery_details(self, d, serial_no, is_submit)
					if d.t_warehouse:
						sl_obj.update_serial_purchase_details(self, d, serial_no, is_submit,
							self.doc.purpose)
					
					if self.doc.purpose == 'Purchase Return':
						serial_doc = Document("Serial No", serial_no)
						serial_doc.status = is_submit and 'Purchase Returned' or 'In Store'
						serial_doc.docstatus = is_submit and 2 or 0
						serial_doc.save()
						
	def update_stock_ledger(self, is_cancelled=0):
		self.values = []			
		for d in getlist(self.doclist, 'mtn_details'):
			if cstr(d.s_warehouse):
				self.add_to_values(d, cstr(d.s_warehouse), -flt(d.transfer_qty), is_cancelled)
			if cstr(d.t_warehouse):
				self.add_to_values(d, cstr(d.t_warehouse), flt(d.transfer_qty), is_cancelled)
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values, 
			self.doc.amended_from and 'Yes' or 'No')

	def update_production_order(self, is_submit):
		if self.doc.production_order:
			# first perform some validations
			# (they are here coz this fn is also called during on_cancel)
			pro_obj = get_obj("Production Order", self.doc.production_order)
			if flt(pro_obj.doc.docstatus) != 1:
				msgprint("""You cannot do any transaction against 
					Production Order : %s, as it's not submitted"""
					% (pro_obj.doc.name), raise_exception=1)
					
			if pro_obj.doc.status == 'Stopped':
				msgprint("""You cannot do any transaction against Production Order : %s, 
					as it's status is 'Stopped'"""% (pro_obj.doc.name), raise_exception=1)
					
			# update bin
			if self.doc.purpose == "Manufacture/Repack":
				pro_obj.doc.produced_qty = flt(pro_obj.doc.produced_qty) + \
					(is_submit and 1 or -1 ) * flt(self.doc.fg_completed_qty)
				args = {
					"item_code": pro_obj.doc.production_item,
					"posting_date": self.doc.posting_date,
					"planned_qty": (is_submit and -1 or 1 ) * flt(self.doc.fg_completed_qty)
				}
				get_obj('Warehouse', pro_obj.doc.fg_warehouse).update_bin(args)
			
			# update production order status
			pro_obj.doc.status = (flt(pro_obj.doc.qty)==flt(pro_obj.doc.produced_qty)) \
				and 'Completed' or 'In Process'
			pro_obj.doc.save()
					
	def get_item_details(self, arg):
		arg = json.loads(arg)

		item = sql("""select stock_uom, description, item_name from `tabItem` 
			where name = %s and (ifnull(end_of_life,'')='' or end_of_life ='0000-00-00' 
			or end_of_life > now())""", (arg.get('item_code')), as_dict = 1)
		if not item: 
			msgprint("Item is not active", raise_exception=1)
						
		ret = {
			'uom'			      	: item and item[0]['stock_uom'] or '',
			'stock_uom'			  	: item and item[0]['stock_uom'] or '',
			'description'		  	: item and item[0]['description'] or '',
			'item_name' 		  	: item and item[0]['item_name'] or '',
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
		uom = sql("""select conversion_factor from `tabUOM Conversion Detail` 
			where parent = %s and uom = %s""", (arg['item_code'], arg['uom']), as_dict = 1)
		if not uom:
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
		self.doclist = self.doc.clear_table(self.doclist, 'mtn_details', 1)
		
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
					item_dict = self.get_bom_raw_materials(self.doc.fg_completed_qty)

				# add raw materials to Stock Entry Detail table
				self.add_to_stock_entry_detail(self.doc.from_warehouse, self.doc.to_warehouse,
					item_dict)
					
			# add finished good item to Stock Entry Detail table -- along with bom_no
			if self.doc.production_order and self.doc.purpose == "Manufacture/Repack":
				self.add_to_stock_entry_detail(None, pro_obj.doc.fg_warehouse, {
					cstr(pro_obj.doc.production_item): 
						[self.doc.fg_completed_qty, pro_obj.doc.description, pro_obj.doc.stock_uom]
				}, bom_no=pro_obj.doc.bom_no)
				
			elif self.doc.purpose in ["Material Receipt", "Manufacture/Repack"]:
				item = webnotes.conn.sql("""select item, description, uom from `tabBOM`
					where name=%s""", (self.doc.bom_no,), as_dict=1)
				self.add_to_stock_entry_detail(None, self.doc.to_warehouse, {
					item[0]["item"] :
						[self.doc.fg_completed_qty, item[0]["description"], item[0]["uom"]]
				}, bom_no=self.doc.bom_no)
		
		self.get_stock_and_rate()
	
	def get_bom_raw_materials(self, qty):
		""" 
			get all items from flat bom except 
			child items of sub-contracted and sub assembly items 
			and sub assembly items itself.
		"""
		# item dict = { item_code: [qty, description, stock_uom] }
		item_dict = {}
		
		def _make_items_dict(items_list):
			"""makes dict of unique items with it's qty"""
			for item in items_list:
				if item_dict.has_key(item.item_code):
					item_dict[item.item_code][0] += flt(item.qty)
				else:
					item_dict[item.item_code] = [flt(item.qty), item.description, item.stock_uom]
		
		if self.doc.use_multi_level_bom:
			# get all raw materials with sub assembly childs					
			fl_bom_sa_child_item = sql("""select 
					item_code,ifnull(sum(qty_consumed_per_unit),0)*%s as qty,
					description,stock_uom 
				from (	select distinct fb.name, fb.description, fb.item_code,
							fb.qty_consumed_per_unit, fb.stock_uom 
						from `tabBOM Explosion Item` fb,`tabItem` it 
						where it.name = fb.item_code and ifnull(it.is_pro_applicable, 'No') = 'No'
						and ifnull(it.is_sub_contracted_item, 'No') = 'No' and fb.docstatus<2 
						and fb.parent=%s
					) a
				group by item_code, stock_uom""" , (qty, self.doc.bom_no), as_dict=1)
			
			if fl_bom_sa_child_item:
				_make_items_dict(fl_bom_sa_child_item)
		else:
			# Get all raw materials considering multi level BOM, 
			# if multi level bom consider childs of Sub-Assembly items
			fl_bom_sa_items = sql("""select item_code,
				ifnull(sum(qty_consumed_per_unit), 0) * '%s' as qty,
				description, stock_uom from `tabBOM Item` 
				where parent = '%s' and docstatus < 2 
				group by item_code""" % (qty, self.doc.bom_no), as_dict=1)
			
			if fl_bom_sa_items:
				_make_items_dict(fl_bom_sa_items)
			
		return item_dict
	
	def get_pending_raw_materials(self, pro_obj):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_qty = self.get_bom_raw_materials(1)
		issued_item_qty = self.get_issued_qty()
		
		max_qty = flt(pro_obj.doc.qty)
		only_pending_fetched = []
		
		for item in item_qty:
			pending_to_issue = (max_qty * item_qty[item][0]) - issued_item_qty.get(item, 0)
			desire_to_transfer = flt(self.doc.fg_completed_qty) * item_qty[item][0]
			
			if desire_to_transfer <= pending_to_issue:
				item_qty[item][0] = desire_to_transfer
			else:
				item_qty[item][0] = pending_to_issue
				if pending_to_issue:
					only_pending_fetched.append(item)
		
		# delete items with 0 qty
		for item in item_qty.keys():
			if not item_qty[item][0]:
				del item_qty[item]
		
		# show some message
		if not len(item_qty):
			webnotes.msgprint(_("""All items have already been transferred \
				for this Production Order."""))
			
		elif only_pending_fetched:
			webnotes.msgprint(_("""Only quantities pending to be transferred \
				were fetched for the following items:\n""" + "\n".join(only_pending_fetched)))

		return item_qty

	def get_issued_qty(self):
		issued_item_qty = {}
		result = sql("""select t1.item_code, sum(t1.qty)
			from `tabStock Entry Detail` t1, `tabStock Entry` t2
			where t1.parent = t2.name and t2.production_order = %s and t2.docstatus = 1
			and t2.purpose = 'Material Transfer'
			group by t1.item_code""", self.doc.production_order)
		for t in result:
			issued_item_qty[t[0]] = flt(t[1])
		
		return issued_item_qty

	def add_to_stock_entry_detail(self, source_wh, target_wh, item_dict, bom_no=None):
		for d in item_dict:
			se_child = addchild(self.doc, 'mtn_details', 'Stock Entry Detail', 
				self.doclist)
			se_child.s_warehouse = source_wh
			se_child.t_warehouse = target_wh
			se_child.item_code = cstr(d)
			se_child.description = item_dict[d][1]
			se_child.uom = item_dict[d][2]
			se_child.stock_uom = item_dict[d][2]
			se_child.qty = flt(item_dict[d][0])
			se_child.transfer_qty = flt(item_dict[d][0])
			se_child.conversion_factor = 1.00
			
			# to be assigned for finished item
			se_child.bom_no = bom_no

	def add_to_values(self, d, wh, qty, is_cancelled):
		self.values.append({
			'item_code': d.item_code,
			'warehouse': wh,
			'posting_date': self.doc.posting_date,
			'posting_time': self.doc.posting_time,
			'voucher_type': 'Stock Entry',
			'voucher_no': self.doc.name, 
			'voucher_detail_no': d.name,
			'actual_qty': qty,
			'incoming_rate': flt(d.incoming_rate) or 0,
			'stock_uom': d.stock_uom,
			'company': self.doc.company,
			'is_cancelled': (is_cancelled ==1) and 'Yes' or 'No',
			'batch_no': cstr(d.batch_no).strip(),
			'serial_no': cstr(d.serial_no).strip()
		})
	
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
		res = sql("select customer_name from `tabCustomer` where name = '%s'"%self.doc.customer)
		addr = self.get_address_text(customer = self.doc.customer)
		ret = { 
			'customer_name'		: res and res[0][0] or '',
			'customer_address' : addr and addr[0] or ''}

		return ret

	def get_supp_values(self):
		result = webnotes.conn.sql("""select supplier, supplier_name,
			address_display as supplier_address
			from `tabPurchase Receipt` where name=%s""", (self.doc.purchase_receipt_no,),
			as_dict=1)
		
		return result and result[0] or {}
		
	def get_supp_addr(self):
		res = sql("""select supplier_name from `tabSupplier`
			where name=%s""", self.doc.supplier)
		addr = self.get_address_text(supplier = self.doc.supplier)
		ret = {
			'supplier_name' : res and res[0][0] or '',
			'supplier_address' : addr and addr[0] or ''}
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
		ifnull(qty, 0) - ifnull(produced_qty, 0) as fg_completed_qty, use_multi_level_bom
		from `tabProduction Order` where name = %s""", production_order, as_dict=1)
	return result and result[0] or {}