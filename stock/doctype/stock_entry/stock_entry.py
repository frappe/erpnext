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

from webnotes.utils import cstr, flt, getdate, now
from webnotes.model import db_exists, delete_doc
from webnotes.model.doc import Document, addchild
from webnotes.model.wrapper import getlist, copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint, _

sql = webnotes.conn.sql
	
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.item_dict = {}
		self.fname = 'mtn_details' 
		
	def validate(self):
		self.validate_serial_nos()

		pro_obj = self.doc.production_order and \
			get_obj('Production Order', self.doc.production_order) or None

		self.validate_warehouse(pro_obj)
		self.validate_production_order(pro_obj)
		self.get_stock_and_rate()
		self.validate_incoming_rate()
		self.validate_bom()
		self.validate_finished_goods()
					
	def validate_serial_nos(self):
		sl_obj = get_obj("Stock Ledger")
		sl_obj.scrub_serial_nos(self)
		sl_obj.validate_serial_no(self, 'mtn_details')
		
	def validate_warehouse(self, pro_obj):
		"""perform various (sometimes conditional) validations on warehouse"""
		
		source_mandatory = ["Material Issue", "Material Transfer",
			"Production Order - Material Transfer", "Purchase Return"]
		target_mandatory = ["Material Receipt", "Material Transfer", 
			"Production Order - Material Transfer", "Sales Return"]
		
		fg_qty = 0
		for d in getlist(self.doclist, 'mtn_details'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.doc.from_warehouse
				d.t_warehouse = self.doc.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				msgprint(_("Atleast one warehouse is mandatory"), raise_exception=1)
			
			if d.s_warehouse == d.t_warehouse:
				msgprint(_("Source and Target Warehouse cannot be same"), raise_exception=1)
				
			if self.doc.purpose in source_mandatory:
				if not d.s_warehouse:
					msgprint(_("Row # ") + "%s: " % cint(d.idx)
						+ _("Source Warehouse") + _(" is mandatory"), raise_exception=1)

				if self.doc.purpose not in target_mandatory:
					d.t_warehouse = None
				
			if self.doc.purpose in target_mandatory:
				if not d.t_warehouse:
					msgprint(_("Row # ") + "%s: " % cint(d.idx)
						+ _("Target Warehouse") + _(" is mandatory"), raise_exception=1)
						
				if self.doc.purpose not in source_mandatory:
					d.s_warehouse = None

			if self.doc.purpose == "Production Order - Update Finished Goods":
				if d.item_code == pro_obj.doc.item:
					d.s_warehouse = None

					if cstr(d.t_warehouse) != pro_obj.doc.fg_warehouse:
						msgprint(_("Row # ") + "%s: " % cint(d.idx)
							+ _("Target Warehouse") + _(" should be same as that in ")
							+ _("Production Order"), raise_exception=1)
				
				else:
					d.t_warehouse = None
					if not d.s_warehouse:
						msgprint(_("Row # ") + "%s: " % cint(d.idx)
							+ _("Source Warehouse") + _(" is mandatory"), raise_exception=1)
				
		# if self.doc.fg_completed_qty and flt(self.doc.fg_completed_qty) != flt(fg_qty):
		# 	msgprint("The Total of FG Qty %s in Stock Entry Detail do not match with FG Completed Qty %s" % (flt(fg_qty), flt(self.doc.fg_completed_qty)))
		# 	raise Exception
		
	def validate_production_order(self, pro_obj=None):
		if not pro_obj:
			pro_obj = get_obj('Production Order', self.doc.production_order)
		
		if self.doc.purpose == "Production Order - Material Transfer":
			self.doc.fg_completed_qty = 0
		
		elif self.doc.purpose == "Production Order - Update Finished Goods":
			if not flt(self.doc.fg_completed_qty):
				msgprint(_("Manufacturing Quantity") + _(" is mandatory"), raise_exception=1)
			
			if flt(pro_obj.doc.qty) < (flt(pro_obj.doc.produced_qty)
					+ flt(self.doc.fg_completed_qty)):
				# do not allow manufacture of qty > production order qty
				msgprint(_("For Item ") + pro_obj.doc.production_item 
					+ _("Quantity already manufactured")
					+ " = %s." % flt(pro_obj.doc.produced_qty)
					+ _("Hence, maximum allowed Manufacturing Quantity")
					+ " = %s." % flt(pro_obj.doc.qty) - flt(pro_obj.doc.produced_qty),
					raise_exception=1)
		else:
			self.doc.production_order = None
			
	def get_stock_and_rate(self):
		"""get stock and incoming rate on posting date"""
		for d in getlist(self.doclist, 'mtn_details'):
			# get actual stock at source warehouse
			d.actual_qty = self.get_as_on_stock(d.item_code, d.s_warehouse or d.t_warehouse, 
				self.doc.posting_date, self.doc.posting_time)

			# get incoming rate
			if not flt(d.incoming_rate):
				d.incoming_rate = self.get_incoming_rate(d.item_code, 
					d.s_warehouse or d.t_warehouse, self.doc.posting_date, 
					self.doc.posting_time, d.transfer_qty, d.serial_no, d.bom_no)
					
	def get_as_on_stock(self, item_code, warehouse, posting_date, posting_time):
		"""Get stock qty on any date"""
		bin = sql("select name from tabBin where item_code = %s and warehouse = %s", 
			(item_code, warehouse))
		if bin:
			prev_sle = get_obj('Bin', bin[0][0]).get_prev_sle(posting_date, posting_time)
			return flt(prev_sle["bin_aqat"])
		else:
			return 0
			
	def get_incoming_rate(self, item_code=None, warehouse=None, 
			posting_date=None, posting_time=None, qty=0, serial_no=None, bom_no=None):
		in_rate = 0

		if bom_no:
			result = flt(webnotes.conn.sql("""select ifnull(total_cost, 0) / ifnull(quantity, 1) 
				from `tabBOM` where name = %s and docstatus=1""", bom_no))
			in_rate = result and result[0][0] or 0
		elif warehouse:
			in_rate = get_obj("Valuation Control").get_incoming_rate(posting_date, posting_time,
				item_code, warehouse, qty, serial_no)
	
		return in_rate
		
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
		for d in getlist(self.doclist, 'mtn_details'):
			if d.bom_no and flt(d.transfer_qty) != flt(self.doc.fg_completed_qty):
				
				

	def get_item_details(self, arg):
		import json
		arg, actual_qty, in_rate = json.loads(arg), 0, 0

		item = sql("select stock_uom, description, item_name from `tabItem` where name = %s and (ifnull(end_of_life,'')='' or end_of_life ='0000-00-00' or end_of_life >	now())", (arg.get('item_code')), as_dict = 1)
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
		uom = sql("select conversion_factor from `tabUOM Conversion Detail` where parent = %s and uom = %s", (arg['item_code'],arg['uom']), as_dict = 1)
		if not uom:
			msgprint("There is no Conversion Factor for UOM '%s' in Item '%s'" % (arg['uom'], arg['item_code']))
			ret = {'uom' : ''}
		else:
			ret = {
				'conversion_factor'		: flt(uom[0]['conversion_factor']),
				'transfer_qty'			: flt(arg['qty']) * flt(uom[0]['conversion_factor']),
			}
		return ret
		
	def get_warehouse_details(self, arg):
		import json
		arg, actual_qty, in_rate = json.loads(arg), 0, 0
		ret = {
			"actual_qty" : self.get_as_on_stock(arg.get('item_code'), arg.get('warehouse'),
			 	self.doc.posting_date, self.doc.posting_time),
			"incoming_rate" : 	self.get_incoming_rate(arg.get('item_code'), 
			 	arg.get('warehouse'), self.doc.posting_date, self.doc.posting_time, 
			 	arg.get('transfer_qty'), arg.get('serial_no'), arg.get('fg_item'),
			 	arg.get('bom_no')) or 0
		}
		return ret
			
	
	def make_items_dict(self, items_list):
		"""makes dict of unique items with it's qty"""
		for i in items_list:
			if self.item_dict.has_key(i[0]):
				self.item_dict[i[0]][0] = flt(self.item_dict[i[0]][0]) + flt(i[1])
			else:
				self.item_dict[i[0]] = [flt(i[1]), cstr(i[2]), cstr(i[3])]
				


	def update_only_remaining_qty(self):
		""" Only pending raw material to be issued to shop floor """
		already_issued_item = {}
		result = sql("""select t1.item_code, sum(t1.qty)
			from `tabStock Entry Detail` t1, `tabStock Entry` t2
			where t1.parent = t2.name and t2.production_order = %s
			and t2.purpose = 'Production Order - Material Transfer' 
			and t2.docstatus = 1 group by t1.item_code""", self.doc.production_order)
		for t in result:
			already_issued_item[t[0]] = flt(t[1])

		for d in self.item_dict.keys():
			self.item_dict[d][0] -= already_issued_item.get(d, 0)
			if self.item_dict[d][0] <= 0:
				del self.item_dict[d]



	def get_raw_materials(self, bom_no, fg_qty, use_multi_level_bom):
		""" 
			get all items from flat bom except 
			child items of sub-contracted and sub assembly items 
			and sub assembly items itself.
		"""
		if use_multi_level_bom:
			# get all raw materials with sub assembly childs					
			fl_bom_sa_child_item = sql("""
				select 
					item_code,ifnull(sum(qty_consumed_per_unit),0)*%s as qty,description,stock_uom 
				from 
					( 
						select distinct fb.name, fb.description, fb.item_code, fb.qty_consumed_per_unit, fb.stock_uom 
						from `tabBOM Explosion Item` fb,`tabItem` it 
						where it.name = fb.item_code and ifnull(it.is_pro_applicable, 'No') = 'No'
						and ifnull(it.is_sub_contracted_item, 'No') = 'No' and fb.docstatus<2 and fb.parent=%s
					) a
				group by item_code,stock_uom
			""" , (fg_qty, bom_no))
			self.make_items_dict(fl_bom_sa_child_item)
		else:
			# Get all raw materials considering multi level BOM, 
			# if multi level bom consider childs of Sub-Assembly items
			fl_bom_sa_items = sql("""
				select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s', description, stock_uom 
				from `tabBOM Item` 
				where parent = '%s' and docstatus < 2 
				group by item_code
			""" % (fg_qty, bom_no))
			
			self.make_items_dict(fl_bom_sa_items)

		# Update only qty remaining to be issued for production
		if self.doc.purpose == 'Production Order - Material Transfer':
			self.update_only_remaining_qty()



	def add_to_stock_entry_detail(self, source_wh, target_wh, item_dict, fg_item = 0, bom_no = ''):
		for d in item_dict:
			se_child = addchild(self.doc, 'mtn_details', 'Stock Entry Detail', 0, self.doclist)
			se_child.s_warehouse = source_wh
			se_child.t_warehouse = target_wh
			se_child.fg_item = fg_item
			se_child.item_code = cstr(d)
			se_child.description = item_dict[d][1]
			se_child.uom = item_dict[d][2]
			se_child.stock_uom = item_dict[d][2]
			se_child.reqd_qty = flt(item_dict[d][0])
			se_child.qty = flt(item_dict[d][0])
			se_child.transfer_qty = flt(item_dict[d][0])
			se_child.conversion_factor = 1.00
			if fg_item: se_child.bom_no = bom_no

	def get_items(self):
		bom_no = self.doc.bom_no
		fg_qty = self.doc.fg_completed_qty
		
		if self.doc.purpose.startswith('Production Order'):
			if not self.doc.production_order:
				webnotes.msgprint(_("Please specify Production Order"), raise_exception=1)
				
			# common validations
			pro_obj = get_obj('Production Order', self.doc.production_order)
			if pro_obj:
				self.validate_production_order(pro_obj)

				bom_no = pro_obj.doc.bom_no
				fg_qty = (self.doc.purpose == 'Production Order - Update Finished Goods') \
				 	and flt(self.doc.fg_completed_qty) or flt(pro_obj.doc.qty)
			
		self.get_raw_materials(bom_no, fg_qty, self.doc.use_multi_level_bom)
		self.doclist = self.doc.clear_table(self.doclist, 'mtn_details', 1)

		# add raw materials to Stock Entry Detail table
		self.add_to_stock_entry_detail(self.doc.from_warehouse, self.doc.to_warehouse,
			self.item_dict)

		# add finished good item to Stock Entry Detail table
		if self.doc.production_order:
			self.add_to_stock_entry_detail(None, pro_obj.doc.fg_warehouse, {
				cstr(pro_obj.doc.production_item): 
					[self.doc.fg_completed_qty, pro_obj.doc.description, pro_obj.doc.stock_uom]
			})
		elif self.doc.bom_no:
			item = webnotes.conn.sql("""select item, description, uom from `tabBOM`
				where name=%s""", (self.doc.bom_no,), as_dict=1)
			self.add_to_stock_entry_detail(None, None, {
				item[0]["item"] :
					[self.doc.fg_completed_qty, item[0]["description"], item[0]["uom"]]
			})
		
		
		
		
		fg_item_dict = {}
		if self.doc.purpose == 'Production Order - Update Finished Goods':
			sw = ''
			tw = cstr(pro_obj.doc.fg_warehouse)	
			fg_item_dict = {
				cstr(pro_obj.doc.production_item) : [self.doc.fg_completed_qty,
				 	pro_obj.doc.description, pro_obj.doc.stock_uom]
			}
		elif self.doc.purpose == 'Other' and self.doc.bom_no:
			sw, tw = '', ''
			item = sql("select item, description, uom from `tabBOM` where name = %s", self.doc.bom_no, as_dict=1)
			fg_item_dict = {
				item[0]['item'] : [self.doc.fg_completed_qty, 
					item[0]['description'], item[0]['uom']]
			}

		if fg_item_dict:
			self.add_to_stock_entry_detail(sw, tw, fg_item_dict, fg_item = 1, bom_no = bom_no)
			
		self.get_stock_and_rate()
			
	def validate_qty_as_per_stock_uom(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if flt(d.transfer_qty) <= 0:
				msgprint("Row No #%s: Qty as per Stock UOM can not be less than \
					or equal to zero" % cint(d.idx), raise_exception=1)


	def add_to_values(self, d, wh, qty, is_cancelled):
		self.values.append({
				'item_code'			    : d.item_code,
				'warehouse'			    : wh,
				'posting_date'		  : self.doc.posting_date,
				'posting_time'		  : self.doc.posting_time,
				'voucher_type'		  : 'Stock Entry',
				'voucher_no'		    : self.doc.name, 
				'voucher_detail_no'	: d.name,
				'actual_qty'		    : qty,
				'incoming_rate'		  : flt(d.incoming_rate) or 0,
				'stock_uom'			    : d.stock_uom,
				'company'			      : self.doc.company,
				'is_cancelled'		  : (is_cancelled ==1) and 'Yes' or 'No',
				'batch_no'			    : d.batch_no,
				'serial_no'         : d.serial_no
		})

	
	def update_stock_ledger(self, is_cancelled=0):
		self.values = []			
		for d in getlist(self.doclist, 'mtn_details'):
			if cstr(d.s_warehouse):
				self.add_to_values(d, cstr(d.s_warehouse), -flt(d.transfer_qty), is_cancelled)
			if cstr(d.t_warehouse):
				self.add_to_values(d, cstr(d.t_warehouse), flt(d.transfer_qty), is_cancelled)
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values, self.doc.amended_from and 'Yes' or 'No')

	def update_production_order(self, is_submit):
		if self.doc.production_order:
			pro_obj = get_obj("Production Order", self.doc.production_order)
			if flt(pro_obj.doc.docstatus) != 1:
				msgprint("""You cannot do any transaction against 
					Production Order : %s, as it's not submitted"""
					% (pro_obj.doc.name), raise_exception=1)
					
			if pro_obj.doc.status == 'Stopped':
				msgprint("""You cannot do any transaction against Production Order : %s, 
					as it's status is 'Stopped'"""% (pro_obj.doc.name), raise_exception=1)
					
			if getdate(pro_obj.doc.posting_date) > getdate(self.doc.posting_date):
				msgprint("""Posting Date of Stock Entry cannot be before Posting Date of 
					Production Order: %s"""% cstr(self.doc.production_order), raise_exception=1)
					
			if self.doc.purpose == "Production Order - Update Finished Goods":
				pro_obj.doc.produced_qty = flt(pro_obj.doc.produced_qty) + \
					(is_submit and 1 or -1 ) * flt(self.doc.fg_completed_qty)
				args = {
					"item_code": pro_obj.doc.production_item,
					"posting_date": self.doc.posting_date,
					"planned_qty": (is_submit and -1 or 1 ) * flt(self.doc.fg_completed_qty)
				}
				get_obj('Warehouse', pro_obj.doc.fg_warehouse).update_bin(args)
				
			pro_obj.doc.status = (flt(pro_obj.doc.qty)==flt(pro_obj.doc.produced_qty)) \
				and 'Completed' or 'In Process'
			pro_obj.doc.save()
	

	# Create / Update Serial No
	# ----------------------------------
	def update_serial_no(self, is_submit):
		sl_obj = get_obj('Stock Ledger')
		if is_submit:
			sl_obj.validate_serial_no_warehouse(self, 'mtn_details')
		
		for d in getlist(self.doclist, 'mtn_details'):
			if d.serial_no:
				serial_nos = sl_obj.get_sr_no_list(d.serial_no)
				for x in serial_nos:
					serial_no = x.strip()
					if d.s_warehouse:
						sl_obj.update_serial_delivery_details(self, d, serial_no, is_submit)
					if d.t_warehouse:
						sl_obj.update_serial_purchase_details(self, d, serial_no, is_submit, self.doc.purpose)
					
					if self.doc.purpose == 'Purchase Return':
						#delete_doc("Serial No", serial_no)
						serial_doc = Document("Serial No", serial_no)
						serial_doc.status = is_submit and 'Purchase Returned' or 'In Store'
						serial_doc.docstatus = is_submit and 2 or 0
						serial_doc.save()


	def on_submit(self):
		self.validate_qty_as_per_stock_uom()
		self.update_serial_no(1)
		self.update_stock_ledger(0)
		# update Production Order
		self.update_production_order(1)


	def on_cancel(self):
		self.update_serial_no(0)
		self.update_stock_ledger(1)
		# update Production Order
		self.update_production_order(0)
		

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
		res = sql("select supplier_name,address from `tabSupplier` where name = '%s'"%self.doc.supplier)
		addr = self.get_address_text(supplier = self.doc.supplier)
		ret = {
			'supplier_name' : res and res[0][0] or '',
			'supplier_address' : addr and addr[0] or ''}
		return ret
