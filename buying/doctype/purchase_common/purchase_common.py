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

from webnotes.utils import add_days, cint, cstr, flt
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _

from buying.utils import get_last_purchase_details

sql = webnotes.conn.sql
	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist

		self.chk_tol_for_list = ['Material Request - Purchase Order', 'Purchase Order - Purchase Receipt', 'Purchase Order - Purchase Invoice']

		self.update_qty = {
			'Material Request - Purchase Order': 'ordered_qty',
			'Purchase Order - Purchase Receipt': 'received_qty',
			'Purchase Order - Purchase Invoice': 'billed_qty',
			'Purchase Receipt - Purchase Invoice': 'billed_qty'
		}

		self.update_percent_field = {
			'Material Request - Purchase Order': 'per_ordered',
			'Purchase Order - Purchase Receipt': 'per_received',
			'Purchase Order - Purchase Invoice': 'per_billed',
			'Purchase Receipt - Purchase Invoice': 'per_billed'
		}

		# used in validation for items and update_prevdoc_detail
		self.doctype_dict = {
			'Material Request': 'Material Request Item',
			'Purchase Order': 'Purchase Order Item',
			'Purchase Receipt': 'Purchase Receipt Item'
		}
 
		self.next_dt_detail = {
			'ordered_qty' : 'Purchase Order Item',
			'billed_qty'	: 'Purchase Invoice Item',
			'received_qty': 'Purchase Receipt Item'
		}

		self.msg = []

	def is_item_table_empty(self, obj):
		if not len(obj.doclist.get({"parentfield": obj.fname})):
			msgprint(_("Hey there! You need to put at least one item in \
				the item table."), raise_exception=True)


	def get_default_schedule_date( self, obj):
		for d in getlist( obj.doclist, obj.fname):
			item = sql("select lead_time_days from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >	now())" % cstr(d.item_code) , as_dict = 1)
			ltd = item and cint(item[0]['lead_time_days']) or 0
			if ltd and obj.doc.transaction_date:
				if d.fields.has_key('lead_time_date') or obj.doc.doctype == 'Material Request':
					d.lead_time_date = cstr(add_days( obj.doc.transaction_date, cint(ltd)))
				if not d.fields.has_key('prevdoc_docname') or (d.fields.has_key('prevdoc_docname') and not d.prevdoc_docname):
					d.schedule_date =	cstr( add_days( obj.doc.transaction_date, cint(ltd)))
				
	# Client Trigger functions
	#------------------------------------------------------------------------------------------------

	# Get Supplier Details 
	def get_supplier_details(self, name = ''):
		details = sql("select supplier_name,address from `tabSupplier` where name = '%s' and docstatus != 2" %(name), as_dict = 1)
		if details:
			ret = {
				'supplier_name'	:	details and details[0]['supplier_name'] or '',
				'supplier_address'	:	details and details[0]['address'] or ''
			}
			# ********** get primary contact details (this is done separately coz. , in case there is no primary contact thn it would not be able to fetch customer details in case of join query)
			contact_det = sql("select contact_name, contact_no, email_id from `tabContact` where supplier = '%s' and is_supplier = 1 and is_primary_contact = 'Yes' and docstatus != 2" %(name), as_dict = 1)
			ret['contact_person'] = contact_det and contact_det[0]['contact_name'] or ''
			return ret
		else:
			msgprint("Supplier : %s does not exists" % (name))
			raise Exception
	
	# Get TERMS AND CONDITIONS
	# =======================================================================================
	def get_tc_details(self,obj):
		r = sql("select terms from `tabTerms and Conditions` where name = %s", obj.doc.tc_name)
		if r: obj.doc.terms = r[0][0]


	# Get Available Qty at Warehouse
	def get_bin_details( self, arg = ''):
		arg = eval(arg)
		bin = sql("select projected_qty from `tabBin` where item_code = %s and warehouse = %s", (arg['item_code'], arg['warehouse']), as_dict=1)
		ret = { 'projected_qty' : bin and flt(bin[0]['projected_qty']) or 0 }
		return ret

	# --- Last Purchase Rate related methods ---
	
	def update_last_purchase_rate(self, obj, is_submit):
		"""updates last_purchase_rate in item table for each item"""
		
		import webnotes.utils
		this_purchase_date = webnotes.utils.getdate(obj.doc.fields.get('posting_date') or obj.doc.fields.get('transaction_date'))
		
		for d in getlist(obj.doclist,obj.fname):
			# get last purchase details
			last_purchase_details = get_last_purchase_details(d.item_code, obj.doc.name)

			# compare last purchase date and this transaction's date
			last_purchase_rate = None
			if last_purchase_details and \
					(last_purchase_details.purchase_date > this_purchase_date):
				last_purchase_rate = last_purchase_details['purchase_rate']
			elif is_submit == 1:
				# even if this transaction is the latest one, it should be submitted
				# for it to be considered for latest purchase rate
				last_purchase_rate = flt(d.purchase_rate) / flt(d.conversion_factor)

			# update last purchsae rate
			if last_purchase_rate:
				sql("update `tabItem` set last_purchase_rate = %s where name = %s",
						(flt(last_purchase_rate),d.item_code))
	
	def get_last_purchase_rate(self, obj):
		"""get last purchase rates for all items"""
		doc_name = obj.doc.name
		conversion_rate = flt(obj.doc.fields.get('conversion_rate')) or 1.0
		
		for d in getlist(obj.doclist, obj.fname):
			if d.item_code:
				last_purchase_details = get_last_purchase_details(d.item_code, doc_name)

				if last_purchase_details:
					d.purchase_ref_rate = last_purchase_details['purchase_ref_rate'] * (flt(d.conversion_factor) or 1.0)
					d.discount_rate = last_purchase_details['discount_rate']
					d.purchase_rate = last_purchase_details['purchase_rate'] * (flt(d.conversion_factor) or 1.0)
					d.import_ref_rate = d.purchase_ref_rate / conversion_rate
					d.import_rate = d.purchase_rate / conversion_rate
				else:
					# if no last purchase found, reset all values to 0
					d.purchase_ref_rate = d.purchase_rate = d.import_ref_rate = d.import_rate = d.discount_rate = 0
					
					item_last_purchase_rate = webnotes.conn.get_value("Item",
						d.item_code, "last_purchase_rate")
					if item_last_purchase_rate:
						d.purchase_ref_rate = d.purchase_rate = d.import_ref_rate \
							= d.import_rate = item_last_purchase_rate
			

	# validate for same items and	validate is_stock_item , is_purchase_item also validate uom and conversion factor
	def validate_for_items(self, obj):
		check_list, chk_dupl_itm=[],[]
		for d in getlist( obj.doclist, obj.fname):
			# validation for valid qty	
			if flt(d.qty) < 0 or (d.parenttype != 'Purchase Receipt' and not flt(d.qty)):
				msgprint("Please enter valid qty for item %s" % cstr(d.item_code))
				raise Exception
			
			# udpate with latest quantities
			bin = sql("select projected_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			
			f_lst ={'projected_qty': bin and flt(bin[0]['projected_qty']) or 0, 'ordered_qty': 0, 'received_qty' : 0, 'billed_qty': 0}
			if d.doctype == 'Purchase Receipt Item':
				f_lst.pop('received_qty')
			for x in f_lst :
				if d.fields.has_key(x):
					d.fields[x] = f_lst[x]
			
			item = sql("select is_stock_item, is_purchase_item, is_sub_contracted_item, end_of_life from tabItem where name=%s", 
				d.item_code)
			if not item:
				msgprint("Item %s does not exist in Item Master." % cstr(d.item_code), raise_exception=True)
			
			from stock.utils import validate_end_of_life
			validate_end_of_life(d.item_code, item[0][3])
			
			# validate stock item
			if item[0][0]=='Yes' and d.qty and not d.warehouse:
				msgprint("Warehouse is mandatory for %s, since it is a stock item" %
				 	d.item_code, raise_exception=1)
			
			# validate purchase item
			if item[0][1] != 'Yes' and item[0][2] != 'Yes':
				msgprint("Item %s is not a purchase item or sub-contracted item. Please check" % (d.item_code), raise_exception=True)
			
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname:
				# check warehouse, uom	in previous doc and in current doc are same.
				data = sql("select item_code, warehouse, uom from `tab%s` where name = '%s'" % ( self.doctype_dict[d.prevdoc_doctype], d.prevdoc_detail_docname), as_dict = 1)
				if not data:
					msgprint("Please fetch data in Row " + cstr(d.idx) + " once again or please contact Administrator.")
					raise Exception
				
				# Check if Item Code has been modified.
				if not cstr(data[0]['item_code']) == cstr(d.item_code):
					msgprint("Please check Item %s is not present in %s %s ." % (d.item_code, d.prevdoc_doctype, d.prevdoc_docname))
					raise Exception
				
				# Check if Warehouse has been modified.
				if not cstr(data[0]['warehouse']) == cstr(d.warehouse):
					msgprint("Please check warehouse %s of Item %s which is not present in %s %s ." % \
						(d.warehouse, d.item_code, d.prevdoc_doctype, d.prevdoc_docname), raise_exception=True)
				
				#	Check if UOM has been modified.
				if not cstr(data[0]['uom']) == cstr(d.uom) and not cstr(d.prevdoc_doctype) == 'Material Request':
					msgprint("Please check UOM %s of Item %s which is not present in %s %s ." % \
						(d.uom, d.item_code, d.prevdoc_doctype, d.prevdoc_docname), raise_exception=True)
			
			# list criteria that should not repeat if item is stock item
			e = [d.schedule_date, d.item_code, d.description, d.warehouse, d.uom, d.fields.has_key('prevdoc_docname') and d.prevdoc_docname or '', d.fields.has_key('prevdoc_detail_docname') and d.prevdoc_detail_docname or '', d.fields.has_key('batch_no') and d.batch_no or '']
			
			# if is not stock item
			f = [d.schedule_date, d.item_code, d.description]
			
			ch = sql("select is_stock_item from `tabItem` where name = '%s'"%d.item_code)
			
			if ch and ch[0][0] == 'Yes':			
				# check for same items
				if e in check_list:
					msgprint("""Item %s has been entered more than once with same description, schedule date, warehouse and uom.\n 
						Please change any of the field value to enter the item twice""" % d.item_code, raise_exception = 1)
				else:
					check_list.append(e)
					
			elif ch and ch[0][0] == 'No':
				# check for same items
				if f in chk_dupl_itm:
					msgprint("""Item %s has been entered more than once with same description, schedule date.\n 
						Please change any of the field value to enter the item twice.""" % d.item_code, raise_exception = 1)
				else:
					chk_dupl_itm.append(f)

	def validate_reference_value(self, obj):
		ref_doc = []
		for d in getlist(obj.doclist, obj.fname):
			if d.prevdoc_doctype and d.prevdoc_docname and d.prevdoc_doctype not in ref_doc:
				mapper_name = d.prevdoc_doctype + '-' + obj.doc.doctype
				get_obj('DocType Mapper', mapper_name, with_children = 1).\
					validate_reference_value(obj, obj.doc.name)
				ref_doc.append(d.prevdoc_doctype)


	# Check for Stopped status 
	def check_for_stopped_status(self, doctype, docname):
		stopped = sql("select name from `tab%s` where name = '%s' and status = 'Stopped'" % 
			( doctype, docname))
		if stopped:
			msgprint("One cannot do any transaction against %s : %s, it's status is 'Stopped'" % 
				( doctype, docname), raise_exception=1)
			
	# Check Docstatus of Next DocType on Cancel AND of Previous DocType on Submit
	def check_docstatus(self, check, doctype, docname , detail_doctype = ''):
		
		if check == 'Next':
			# Convention := doctype => Next Doctype, docname = current_docname , detail_doctype = Next Doctype Detail Table

			submitted = sql("select t1.name from `tab%s` t1,`tab%s` t2 where t1.name = t2.parent and t2.prevdoc_docname = '%s' and t1.docstatus = 1" % ( doctype, detail_doctype, docname))
			if submitted:
				msgprint(cstr(doctype) + " : " + cstr(submitted[0][0]) + " has already been submitted !")
				raise Exception

		if check == 'Previous':
			# Convention := doctype => Previous Doctype, docname = Previous Docname 
			submitted = sql("select name from `tab%s` where docstatus = 1 and name = '%s'" % (doctype, docname))
			if not submitted:
				msgprint(cstr(doctype) + " : " + cstr(submitted[0][0]) + " not submitted !")
				raise Exception
				
	# Update Ref Doc
	# =======================================================
	def get_qty(self,curr_doctype,ref_tab_fname,ref_tab_dn,ref_doc_tname, transaction, curr_parent_name):
		# Get total Quantities of current doctype (eg. PR) except for qty of this transaction
		#------------------------------
		# please check as UOM changes from Material Request - Purchase Order ,so doing following else uom should be same .
		# i.e. in PO uom is NOS then in PR uom should be NOS
		# but if in Material Request uom KG it can change in PO
		
		get_qty = (transaction == 'Material Request - Purchase Order') and 'qty * conversion_factor' or 'qty'
		qty = sql("select sum(%s) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% ( get_qty, curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
		qty = qty and flt(qty[0][0]) or 0 
		
		# get total qty of ref doctype
		#--------------------
		max_qty = sql("select qty from `tab%s` where name = '%s' and docstatus = 1"% (ref_doc_tname, ref_tab_dn))
		max_qty = max_qty and flt(max_qty[0][0]) or 0
		
		return cstr(qty)+'~~~'+cstr(max_qty)	



	def update_refdoc_qty(self, curr_qty, curr_doctype, ref_dn, ref_dt, ref_tab_fname, ref_tab_dn, transaction, item_code, is_submit, curr_parent_doctype, curr_parent_name):
		# Get Quantity
		#------------------------------
		curr_ref_qty = self.get_qty(curr_doctype,ref_tab_fname,ref_tab_dn,self.doctype_dict[ref_dt], transaction, curr_parent_name)
		qty, max_qty, max_qty_plus_tol = flt(curr_ref_qty.split('~~~')[0]), flt(curr_ref_qty.split('~~~')[1]), flt(curr_ref_qty.split('~~~')[1])

		# Qty above Tolerance should be allowed only once.
		# But there is special case for Transaction 'Material Request-Purhcase Order' that there should be no restriction
		# One can create any no. of PO against same Material Request!!!
		if qty >= max_qty and is_submit and flt(curr_qty) > 0:
			reason = (curr_parent_doctype == 'Purchase Order') and 'Ordered' or (curr_parent_doctype == 'Purchase Receipt') and 'Received' or (curr_parent_doctype == 'Purchase Invoice') and 'Billed'
			msgprint("Error: Item Code : '%s' of '%s' is already %s." %(item_code,ref_dn,reason))
			raise Exception
		
		#check if tolerance added in item master
		tolerance = flt(webnotes.conn.get_value('Item',item_code,'tolerance') or 0)
		
		if not(tolerance):
			tolerance = flt(webnotes.conn.get_value('Global Defaults',None,'tolerance') or 0)

		if is_submit:
			qty = qty + flt(curr_qty)
			
			# Calculate max_qty_plus_tol i.e. max_qty with tolerance 
			#-----------------------------------------------------------------
			if transaction in self.chk_tol_for_list:
				max_qty_plus_tol = max_qty * (1 + (flt(tolerance)/ 100))

				if max_qty_plus_tol < qty:
					reason = (curr_parent_doctype == 'Purchase Order') and 'Ordered' or (curr_parent_doctype == 'Purchase Receipt') and 'Received' or (curr_parent_doctype == 'Purchase Invoice') and 'Billed'
					msg = "error: Already %s Qty for %s is %s and \
						maximum allowed Qty is %s [against %s: %s]" % \
						(cstr(reason), item_code,
						cstr(flt(qty) - flt(curr_qty)) , cstr(max_qty_plus_tol),
						cstr(ref_dt), cstr(ref_dn))
					msgprint(msg, raise_exception=1)

		# Update qty
		#------------------
		sql("update `tab%s` set %s = '%s',modified = now() where name = '%s'" % (self.doctype_dict[ref_dt],self.update_qty[transaction] , flt(qty), ref_tab_dn))
		
	def update_ref_doctype_dict(self, curr_qty, curr_doctype, ref_dn, ref_dt, ref_tab_fname, ref_tab_dn, transaction, item_code, is_submit, curr_parent_doctype, curr_parent_name):
		# update qty 
		self.update_refdoc_qty( curr_qty, curr_doctype, ref_dn, ref_dt, ref_tab_fname, ref_tab_dn, transaction, item_code, is_submit, curr_parent_doctype, curr_parent_name)
		
		# append distinct ref_dn in doctype_dict
		if not self.ref_doctype_dict.has_key(ref_dn) and self.update_percent_field.has_key(transaction):
			self.ref_doctype_dict[ref_dn] = [ ref_dt, self.doctype_dict[ref_dt],transaction]


	# update prevdoc detail
	# --------------------
	def update_prevdoc_detail(self, obj, is_submit):
		import math
		self.ref_doctype_dict= {}
		for d in getlist(obj.doclist, obj.fname):
			
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname:
				transaction = cstr(d.prevdoc_doctype) + ' - ' + cstr(obj.doc.doctype)
				curr_qty = (transaction == 'Material Request - Purchase Order') and flt(d.qty) * flt(d.conversion_factor) or flt(d.qty)
				self.update_ref_doctype_dict( flt(curr_qty), d.doctype, d.prevdoc_docname, d.prevdoc_doctype, 'prevdoc_detail_docname', d.prevdoc_detail_docname, transaction, d.item_code, is_submit, obj.doc.doctype, obj.doc.name)
			
			# for payable voucher
			if d.fields.has_key('purchase_order') and d.purchase_order:
				curr_qty = sql("select sum(qty) from `tabPurchase Invoice Item` where po_detail = '%s' and parent = '%s'" % (cstr(d.po_detail), cstr(obj.doc.name)))
				curr_qty = curr_qty and flt(curr_qty[0][0]) or 0
				self.update_ref_doctype_dict( curr_qty, d.doctype, d.purchase_order, 'Purchase Order', 'po_detail', d.po_detail, 'Purchase Order - ' + cstr(obj.doc.doctype), d.item_code, is_submit,	obj.doc.doctype, obj.doc.name)

			if d.fields.has_key('purchase_receipt') and d.purchase_receipt:
				 self.update_ref_doctype_dict( flt(d.qty), d.doctype, d.purchase_receipt, 'Purchase Receipt', 'pr_detail', d.pr_detail, 'Purchase Receipt - ' + cstr(obj.doc.doctype), d.item_code, is_submit,	obj.doc.doctype, obj.doc.name)
			
		for ref_dn in self.ref_doctype_dict:
			# Calculate percentage
			#----------------------
			ref_doc_obj = get_obj(self.ref_doctype_dict[ref_dn][0],ref_dn,with_children = 1)
			count = 0
			percent = 0
			for d in getlist(ref_doc_obj.doclist,ref_doc_obj.fname):
				ref_qty = d.fields[self.update_qty[self.ref_doctype_dict[ref_dn][2]]]
				if flt(d.qty) - flt(ref_qty) <= 0:
					percent += 100
				else:
					percent += (flt(ref_qty)/flt(d.qty) * 100)
				count += 1
			percent_complete = math.floor(flt(percent)/ flt(count))
			
			# update percent complete and modified
			#-------------------------------------
			sql("update `tab%s` set %s = '%s', modified = '%s' where name = '%s'" % (self.ref_doctype_dict[ref_dn][0], self.update_percent_field[self.ref_doctype_dict[ref_dn][2]], percent_complete, obj.doc.modified, ref_dn))
			
			
	def validate_fiscal_year(self, fiscal_year, transaction_date, dn):
		fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%fiscal_year)
		ysd=fy and fy[0][0] or ""
		yed=add_days(str(ysd),365)		
		if str(transaction_date) < str(ysd) or str(transaction_date) > str(yed):
			msgprint("'%s' Not Within The Fiscal Year"%(dn))
			raise Exception

	def load_default_taxes(self, obj):
		return self.get_purchase_tax_details(obj, 1)
	
	def get_purchase_tax_details(self,obj, default = 0):
		obj.doclist = self.doc.clear_table(obj.doclist,'purchase_tax_details')
		
		if default: add_cond = " and ifnull(t2.is_default,0) = 1"
		else: add_cond = " and t1.parent = '"+cstr(obj.doc.purchase_other_charges)+"'"

		other_charge = sql("""
			select t1.*
			from `tabPurchase Taxes and Charges` t1, `tabPurchase Taxes and Charges Master` t2
			where t1.parent = t2.name %s
			order by t1.idx
		"""% add_cond, as_dict = 1)
		
		idx = 0
		for other in other_charge:
			d =	addchild(obj.doc, 'purchase_tax_details', 'Purchase Taxes and Charges', 
				obj.doclist)
			d.category = other['category']
			d.add_deduct_tax = other['add_deduct_tax']
			d.charge_type = other['charge_type']
			d.row_id = other['row_id']
			d.description = other['description']
			d.account_head = other['account_head']
			d.rate = flt(other['rate'])
			d.tax_amount = flt(other['tax_amount'])
			d.cost_center = other["cost_center"]
			d.idx = idx
			idx += 1
		return obj.doclist

	def get_rate(self, arg, obj):
		arg = eval(arg)
		rate = sql("select account_type, tax_rate from `tabAccount` where name = '%s'" %(arg['account_head']), as_dict=1)
		
		return {'rate':	rate and (rate[0]['account_type'] == 'Tax' \
			and not arg['charge_type'] == 'Actual') and flt(rate[0]['tax_rate']) or 0 }

	def get_prevdoc_date(self, obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.prevdoc_doctype and d.prevdoc_docname:
				dt = sql("select transaction_date from `tab%s` where name = '%s'" % (d.prevdoc_doctype, d.prevdoc_docname))
				d.prevdoc_date = dt and dt[0][0].strftime('%Y-%m-%d') or ''

@webnotes.whitelist()
def get_uom_details(args=None):
	"""fetches details on change of UOM"""
	if not args:
		return {}
		
	if isinstance(args, basestring):
		import json
		args = json.loads(args)

	uom = webnotes.conn.sql("""select conversion_factor
		from `tabUOM Conversion Detail` where parent = %s and uom = %s""", 
		(args['item_code'], args['uom']), as_dict=1)

	if not uom: return {}

	conversion_factor = args.get("conversion_factor") or \
		flt(uom[0]["conversion_factor"])
	
	return {
		"conversion_factor": conversion_factor,
		"qty": flt(args["stock_qty"]) / conversion_factor,
	}
