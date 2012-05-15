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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists, delete_doc
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.item_dict = {}
		self.fname = 'mtn_details' 

	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')

  
	# get item details
	# ----------------
	def get_item_details(self, arg):
		import json
		arg, actual_qty, in_rate = json.loads(arg), 0, 0

		item = sql("select stock_uom, description, item_name from `tabItem` where name = %s and (ifnull(end_of_life,'')='' or end_of_life ='0000-00-00' or end_of_life >	now())", (arg.get('item_code')), as_dict = 1)
		if not item: 
			msgprint("Item is not active", raise_exception=1)
			
		if arg.get('warehouse'):
			actual_qty = self.get_as_on_stock(arg.get('item_code'), arg.get('warehouse'), self.doc.posting_date, self.doc.posting_time)
			in_rate = self.get_incoming_rate(arg.get('item_code'), arg.get('warehouse'), self.doc.posting_date, self.doc.posting_time, arg.get('transfer_qty'), arg.get('serial_no')) or 0
			
		ret = {
			'uom'			      	: item and item[0]['stock_uom'] or '',
			'stock_uom'			  	: item and item[0]['stock_uom'] or '',
			'description'		  	: item and item[0]['description'] or '',
			'item_name' 		  	: item and item[0]['item_name'] or '',
			'actual_qty'		  	: actual_qty,
			'qty'					: 0,
			'transfer_qty'			: 0,
			'incoming_rate'	  		: in_rate,
			'conversion_factor'		: 1,
     		'batch_no'          	: ''
		}
		return ret


	# Get UOM Details
	# ----------------
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

		

	# get stock and incoming rate on posting date
	# ---------------------------------------------
	def get_stock_and_rate(self, bom_no = ''):
		for d in getlist(self.doclist, 'mtn_details'):
			# assign parent warehouse
			d.s_warehouse = cstr(d.s_warehouse) or self.doc.purpose != 'Production Order' and self.doc.from_warehouse or ''
			d.t_warehouse = cstr(d.t_warehouse) or self.doc.purpose != 'Production Order' and self.doc.to_warehouse or ''
			
			# get current stock at source warehouse
			d.actual_qty = d.s_warehouse and self.get_as_on_stock(d.item_code, d.s_warehouse, self.doc.posting_date, self.doc.posting_time) or 0

			# get incoming rate
			if not flt(d.incoming_rate):
				d.incoming_rate = self.get_incoming_rate(d.item_code, d.s_warehouse, self.doc.posting_date, self.doc.posting_time, d.transfer_qty, d.serial_no, d.fg_item, d.bom_no or bom_no)


	# Get stock qty on any date
	# ---------------------------
	def get_as_on_stock(self, item, wh, dt, tm):
		bin = sql("select name from tabBin where item_code = %s and warehouse = %s", (item, wh))
		bin_id = bin and bin[0][0] or ''
		prev_sle = bin_id and get_obj('Bin', bin_id).get_prev_sle(dt, tm) or {}		
		qty = flt(prev_sle.get('bin_aqat', 0))
		return qty


	# Get incoming rate
	# -------------------
	def get_incoming_rate(self, item, wh, dt, tm, qty = 0, serial_no = '', fg_item = 0, bom_no = ''):
		in_rate = 0
		if fg_item and bom_no:
			# re-calculate cost for production item from bom
			get_obj('BOM Control').calculate_cost(bom_no)
			bom_obj = get_obj('BOM', bom_no)
			in_rate = flt(bom_obj.doc.total_cost) / (flt(bom_obj.doc.quantity) or 1)
		elif wh:
			in_rate = get_obj('Valuation Control').get_incoming_rate(dt, tm, item, wh, qty, serial_no)
		
		return in_rate



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
		for t in sql("""select t1.item_code, sum(t1.qty) from `tabStock Entry Detail` t1, `tabStock Entry` t2
				where t1.parent = t2.name and t2.production_order = %s and t2.process = 'Material Transfer' 
				and t2.docstatus = 1 group by t1.item_code""", self.doc.production_order):
			already_issued_item[t[0]] = flt(t[1])

		for d in self.item_dict.keys():
			self.item_dict[d][0] -= already_issued_item.get(d, 0)
			if self.item_dict[d][0] <= 0:
				del self.item_dict[d]



	def get_raw_materials(self, bom_no, fg_qty, consider_sa_items_as_rm):
		""" 
			get all items from flat bom except 
			child items of sub-contracted and sub assembly items 
			and sub assembly items itself.
		"""
		if consider_sa_items_as_rm == 'Yes':
			# Get all raw materials considering SA items as raw materials, 
			# so no childs of SA items
			fl_bom_sa_items = sql("""
				select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s', description, stock_uom 
				from `tabBOM Item` 
				where parent = '%s' and docstatus < 2 
				group by item_code
			""" % (fg_qty, bom_no))
			
			self.make_items_dict(fl_bom_sa_items)

		else:
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

		# Update only qty remaining to be issued for production
		if self.doc.process == 'Material Transfer':
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

	def validate_bom_no(self):
		if self.doc.bom_no:
			if not self.doc.fg_completed_qty:
				msgprint("Please enter FG Completed Qty", raise_exception=1)
			if not self.doc.consider_sa_items_as_raw_materials:
				msgprint("Please confirm whether you want to consider sub assembly item as raw materials", raise_exception=1)	


	# get items 
	#------------------
	def get_items(self):
		if self.doc.purpose == 'Production Order':
			pro_obj = self.doc.production_order and get_obj('Production Order', self.doc.production_order) or ''	
			self.validate_for_production_order(pro_obj)

			bom_no = pro_obj.doc.bom_no
			fg_qty = (self.doc.process == 'Backflush') and flt(self.doc.fg_completed_qty) or flt(pro_obj.doc.qty)
			consider_sa_items_as_rm = pro_obj.doc.consider_sa_items
		elif self.doc.purpose == 'Other':
			self.validate_bom_no()
			bom_no = self.doc.bom_no
			fg_qty = self.doc.fg_completed_qty
			consider_sa_items_as_rm = self.doc.consider_sa_items_as_raw_materials
			
		self.get_raw_materials(bom_no, fg_qty, consider_sa_items_as_rm)
		self.doc.clear_table(self.doclist, 'mtn_details', 1)

		sw = (self.doc.process == 'Backflush') and cstr(pro_obj.doc.wip_warehouse) or ''
		tw = (self.doc.process == 'Material Transfer') and cstr(pro_obj.doc.wip_warehouse) or ''
		self.add_to_stock_entry_detail(sw, tw, self.item_dict)

		fg_item_dict = {}
		if self.doc.process == 'Backflush':
			sw = ''
			tw = cstr(pro_obj.doc.fg_warehouse)	
			fg_item_dict = {cstr(pro_obj.doc.production_item) : [self.doc.fg_completed_qty, pro_obj.doc.description, pro_obj.doc.stock_uom]}
		elif self.doc.purpose == 'Other' and self.doc.bom_no:
			sw, tw = '', ''
			item = sql("select item, description, uom from `tabBOM` where name = %s", self.doc.bom_no, as_dict=1)
			fg_item_dict = {item[0]['item'] : [self.doc.fg_completed_qty, item[0]['description'], item[0]['uom']]}

		if fg_item_dict:
			self.add_to_stock_entry_detail(sw, tw, fg_item_dict, fg_item = 1, bom_no = bom_no)
			


	def validate_transfer_qty(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if flt(d.transfer_qty) <= 0:
				msgprint("Transfer Quantity can not be less than or equal to zero at Row No " + cstr(d.idx))
				raise Exception


	def calc_amount(self):
		total_amount = 0
		for d in getlist(self.doclist, 'mtn_details'):
			d.amount = flt(d.transfer_qty) * flt(d.incoming_rate)
			total_amount += flt(d.amount)
		self.doc.total_amount = flt(total_amount)


	def add_to_values(self, d, wh, qty, is_cancelled):
		self.values.append({
				'item_code'			    : d.item_code,
				'warehouse'			    : wh,
				'transaction_date'	: self.doc.transfer_date,
				'posting_date'		  : self.doc.posting_date,
				'posting_time'		  : self.doc.posting_time,
				'voucher_type'		  : 'Stock Entry',
				'voucher_no'		    : self.doc.name, 
				'voucher_detail_no'	: d.name,
				'actual_qty'		    : qty,
				'incoming_rate'		  : flt(d.incoming_rate) or 0,
				'stock_uom'			    : d.stock_uom,
				'company'			      : self.doc.company,
				'fiscal_year'		    : self.doc.fiscal_year,
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

	
	def validate_for_production_order(self, pro_obj):
		if self.doc.purpose == 'Production Order' or self.doc.process or self.doc.production_order:
			if self.doc.purpose != 'Production Order':
				msgprint("Purpose should be 'Production Order'.")
				raise Exception
			if not self.doc.process:
				msgprint("Process Field is mandatory.")
				raise Exception
			if self.doc.process == 'Backflush' and not flt(self.doc.fg_completed_qty):
				msgprint("FG Completed Qty is mandatory as the process selected is 'Backflush'")
				raise Exception
			if self.doc.process == 'Material Transfer' and flt(self.doc.fg_completed_qty):
				msgprint("FG Completed Qty should be zero. As the Process selected is 'Material Transfer'.")
				raise Exception
			if not self.doc.production_order:
				msgprint("Production Order field is mandatory")
				raise Exception
			if flt(pro_obj.doc.qty) < flt(pro_obj.doc.produced_qty) + flt(self.doc.fg_completed_qty) :
				msgprint("error:Already Produced Qty for %s is %s and maximum allowed Qty is %s" % (pro_obj.doc.production_item, cstr(pro_obj.doc.produced_qty) or 0.00 , cstr(pro_obj.doc.qty)))
				raise Exception
	

	def validate(self):
		sl_obj = get_obj("Stock Ledger", "Stock Ledger")
		sl_obj.scrub_serial_nos(self)
		sl_obj.validate_serial_no(self, 'mtn_details')
		pro_obj = ''
		if self.doc.production_order:
			pro_obj = get_obj('Production Order', self.doc.production_order)
		self.validate_for_production_order(pro_obj)
		self.get_stock_and_rate(pro_obj and pro_obj.doc.bom_no or '')
		self.validate_warehouse(pro_obj)
		self.validate_incoming_rate()
		self.validate_bom_belongs_to_item()
		self.calc_amount()
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')
		
	
	# If target warehouse exists, incoming rate is mandatory
	# --------------------------------------------------------
	def validate_incoming_rate(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if not flt(d.incoming_rate) and d.t_warehouse:
				msgprint("Rate is mandatory for Item: %s at row %s" % (d.item_code, d.idx), raise_exception=1)
	
	
	def validate_bom_belongs_to_item(self):
		for d in getlist(self.doclist, 'mtn_details'):
			if d.bom_no and not webnotes.conn.sql("""\
					SELECT name FROM `tabBOM`
					WHERE item = %s and name = %s
				""", (d.item_code, d.bom_no)):
				msgprint("BOM %s does not belong to Item: %s at row %s" % (d.bom_no, d.item_code, d.idx), raise_exception=1)


	# Validate warehouse
	# -----------------------------------
	def validate_warehouse(self, pro_obj):
		fg_qty = 0
		for d in getlist(self.doclist, 'mtn_details'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.doc.from_warehouse
				d.t_warehouse = self.doc.to_warehouse

			if not (d.s_warehouse or d.t_warehouse):
				msgprint("Atleast one warehouse is mandatory for Stock Entry ")
				raise Exception
			if d.s_warehouse and not sql("select name from tabWarehouse where name = '%s'" % d.s_warehouse):
				msgprint("Invalid Warehouse: %s" % self.doc.s_warehouse)
				raise Exception
			if d.t_warehouse and not sql("select name from tabWarehouse where name = '%s'" % d.t_warehouse):
				msgprint("Invalid Warehouse: %s" % self.doc.t_warehouse)
				raise Exception
			if d.s_warehouse == d.t_warehouse:
				msgprint("Source and Target Warehouse Cannot be Same.")
				raise Exception
			if self.doc.purpose == 'Material Issue':
				if not cstr(d.s_warehouse):
					msgprint("Source Warehouse is Mandatory for Purpose => 'Material Issue'")
					raise Exception
				if cstr(d.t_warehouse):
					msgprint("Target Warehouse is not Required for Purpose => 'Material Issue'")
					raise Exception
			if self.doc.purpose == 'Material Transfer':
				if not cstr(d.s_warehouse) or not cstr(d.t_warehouse):
					msgprint("Source Warehouse and Target Warehouse both are Mandatory for Purpose => 'Material Transfer'")
					raise Exception
			if self.doc.purpose == 'Material Receipt':
				if not cstr(d.t_warehouse):
					msgprint("Target Warehouse is Mandatory for Purpose => 'Material Receipt'")
					raise Exception
				if cstr(d.s_warehouse):
					msgprint("Source Warehouse is not Required for Purpose => 'Material Receipt'")
					raise Exception
			if self.doc.process == 'Material Transfer':
				if cstr(d.t_warehouse) != (pro_obj.doc.wip_warehouse):
					msgprint(" Target Warehouse should be same as WIP Warehouse %s in Production Order %s at Row No %s" % (cstr(pro_obj.doc.wip_warehouse), cstr(pro_obj.doc.name), cstr(d.idx)) )
					raise Exception
				if not cstr(d.s_warehouse):
					msgprint("Please Enter Source Warehouse at Row No %s." % (cstr(d.idx)))
					raise Exception
			if self.doc.process == 'Backflush':
				if flt(d.fg_item):
					if cstr(pro_obj.doc.production_item) != cstr(d.item_code):
						msgprint("Item %s in Stock Entry Detail as Row No %s do not match with Item %s in Production Order %s" % (cstr(d.item_code), cstr(d.idx), cstr(pro_obj.doc.production_item), cstr(pro_obj.doc.name)))
						raise Exception
					if cstr(d.t_warehouse) != cstr(pro_obj.doc.fg_warehouse):
						msgprint("As Item %s is FG Item. Target Warehouse should be same as FG Warehouse %s in Production Order %s, at Row No %s. " % ( cstr(d.item_code), cstr(pro_obj.doc.fg_warehouse), cstr(pro_obj.doc.name), cstr(d.idx)))
						raise Exception
					if cstr(d.s_warehouse):
						msgprint("As Item %s is a FG Item. There should be no Source Warehouse at Row No %s" % (cstr(d.item_code), cstr(d.idx)))
						raise Exception
				if not flt(d.fg_item):
					if cstr(d.t_warehouse):
						msgprint("As Item %s is not a FG Item. There should no Tareget Warehouse at Row No %s" % (cstr(d.item_code), cstr(d.idx)))
						raise Exception
					if cstr(d.s_warehouse) != cstr(pro_obj.doc.wip_warehouse):
						msgprint("As Item %s is Raw Material. Source Warehouse should be same as WIP Warehouse %s in Production Order %s, at Row No %s. " % ( cstr(d.item_code), cstr(pro_obj.doc.wip_warehouse), cstr(pro_obj.doc.name), cstr(d.idx)))
						raise Exception
			if d.fg_item and (self.doc.purpose == 'Other' or self.doc.process == 'Backflush'):
				fg_qty = flt(fg_qty) + flt(d.transfer_qty)

			d.save()
		if self.doc.fg_completed_qty and flt(self.doc.fg_completed_qty) != flt(fg_qty):
			msgprint("The Total of FG Qty %s in Stock Entry Detail do not match with FG Completed Qty %s" % (flt(fg_qty), flt(self.doc.fg_completed_qty)))
			raise Exception


	def update_production_order(self, is_submit):
		if self.doc.production_order:
			pro_obj = get_obj("Production Order", self.doc.production_order)
			if flt(pro_obj.doc.docstatus) != 1:
				msgprint("You cannot do any transaction against Production Order : %s, as it's not submitted" % (pro_obj.doc.name))
				raise Exception
			if pro_obj.doc.status == 'Stopped':
				msgprint("You cannot do any transaction against Production Order : %s, as it's status is 'Stopped'" % (pro_obj.doc.name))
				raise Exception
			if getdate(pro_obj.doc.posting_date) > getdate(self.doc.posting_date):
				msgprint("Posting Date of Stock Entry cannot be before Posting Date of Production Order "+ cstr(self.doc.production_order))
				raise Exception
			if self.doc.process == 'Backflush':
				pro_obj.doc.produced_qty = flt(pro_obj.doc.produced_qty) + (is_submit and 1 or -1 ) * flt(self.doc.fg_completed_qty)
				get_obj('Warehouse', pro_obj.doc.fg_warehouse).update_bin(0, 0, 0, 0, (is_submit and 1 or -1 ) * flt(self.doc.fg_completed_qty), pro_obj.doc.production_item, now())
			pro_obj.doc.status = (flt(pro_obj.doc.qty) == flt(pro_obj.doc.produced_qty)) and 'Completed' or 'In Process'
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
		self.validate_transfer_qty()
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.total_amount)
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
		tbl = self.doc.delivery_note_no and 'Delivery Note' or 'Sales Invoice'
		record_name = self.doc.delivery_note_no or self.doc.sales_invoice_no
		res = sql("select customer,customer_name, customer_address from `tab%s` where name = '%s'" % (tbl, record_name))
		ret = {
			'customer'				 : res and res[0][0] or '',
			'customer_name'		: res and res[0][1] or '',
			'customer_address' : res and res[0][2] or ''}

		return ret


	def get_cust_addr(self):
		res = sql("select customer_name from `tabCustomer` where name = '%s'"%self.doc.customer)
		addr = self.get_address_text(customer = self.doc.customer)
		ret = { 
			'customer_name'		: res and res[0][0] or '',
			'customer_address' : addr and addr[0] or ''}

		return ret


		
	def get_supp_values(self):
		res = sql("select supplier,supplier_name,supplier_address from `tabPurchase Receipt` where name = '%s'"%self.doc.purchase_receipt_no)
		ret = {
			'supplier' : res and res[0][0] or '',
			'supplier_name' :res and res[0][1] or '',
			'supplier_address' : res and res[0][2] or ''}
		return ret
		

	def get_supp_addr(self):
		res = sql("select supplier_name,address from `tabSupplier` where name = '%s'"%self.doc.supplier)
		addr = self.get_address_text(supplier = self.doc.supplier)
		ret = {
			'supplier_name' : res and res[0][0] or '',
			'supplier_address' : addr and addr[0] or ''}
		return ret
