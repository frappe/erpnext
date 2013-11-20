# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt
from webnotes.model.utils import getlist
from webnotes import msgprint, _

from buying.utils import get_last_purchase_details

	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=None):
		self.doc = doc
		self.doclist = doclist
	
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
				if flt(d.conversion_factor):
					last_purchase_rate = flt(d.purchase_rate) / flt(d.conversion_factor)
				else:
					msgprint(_("Row ") + cstr(d.idx) + ": " + 
						_("UOM Conversion Factor is mandatory"), raise_exception=1)

			# update last purchsae rate
			if last_purchase_rate:
				webnotes.conn.sql("update `tabItem` set last_purchase_rate = %s where name = %s",
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
			
	def validate_for_items(self, obj):
		check_list, chk_dupl_itm=[],[]
		for d in getlist( obj.doclist, obj.fname):
			# validation for valid qty	
			if flt(d.qty) < 0 or (d.parenttype != 'Purchase Receipt' and not flt(d.qty)):
				msgprint("Please enter valid qty for item %s" % cstr(d.item_code))
				raise Exception
			
			# udpate with latest quantities
			bin = webnotes.conn.sql("select projected_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			
			f_lst ={'projected_qty': bin and flt(bin[0]['projected_qty']) or 0, 'ordered_qty': 0, 'received_qty' : 0}
			if d.doctype == 'Purchase Receipt Item':
				f_lst.pop('received_qty')
			for x in f_lst :
				if d.fields.has_key(x):
					d.fields[x] = f_lst[x]
			
			item = webnotes.conn.sql("select is_stock_item, is_purchase_item, is_sub_contracted_item, end_of_life from tabItem where name=%s", 
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
			
			# list criteria that should not repeat if item is stock item
			e = [d.schedule_date, d.item_code, d.description, d.warehouse, d.uom, d.fields.has_key('prevdoc_docname') and d.prevdoc_docname or '', d.fields.has_key('prevdoc_detail_docname') and d.prevdoc_detail_docname or '', d.fields.has_key('batch_no') and d.batch_no or '']
			
			# if is not stock item
			f = [d.schedule_date, d.item_code, d.description]
			
			ch = webnotes.conn.sql("select is_stock_item from `tabItem` where name = '%s'"%d.item_code)
			
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
					
	def get_qty(self,curr_doctype,ref_tab_fname,ref_tab_dn,ref_doc_tname, transaction, curr_parent_name):
		# Get total Quantities of current doctype (eg. PR) except for qty of this transaction
		#------------------------------
		# please check as UOM changes from Material Request - Purchase Order ,so doing following else uom should be same .
		# i.e. in PO uom is NOS then in PR uom should be NOS
		# but if in Material Request uom KG it can change in PO
		
		get_qty = (transaction == 'Material Request - Purchase Order') and 'qty * conversion_factor' or 'qty'
		qty = webnotes.conn.sql("select sum(%s) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% ( get_qty, curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
		qty = qty and flt(qty[0][0]) or 0 
		
		# get total qty of ref doctype
		#--------------------
		max_qty = webnotes.conn.sql("select qty from `tab%s` where name = '%s' and docstatus = 1"% (ref_doc_tname, ref_tab_dn))
		max_qty = max_qty and flt(max_qty[0][0]) or 0
		
		return cstr(qty)+'~~~'+cstr(max_qty)

	def check_for_stopped_status(self, doctype, docname):
		stopped = webnotes.conn.sql("select name from `tab%s` where name = '%s' and status = 'Stopped'" % 
			( doctype, docname))
		if stopped:
			msgprint("One cannot do any transaction against %s : %s, it's status is 'Stopped'" % 
				( doctype, docname), raise_exception=1)
	
	def check_docstatus(self, check, doctype, docname , detail_doctype = ''):
		if check == 'Next':
			submitted = webnotes.conn.sql("""select t1.name from `tab%s` t1,`tab%s` t2 
				where t1.name = t2.parent and t2.prevdoc_docname = %s and t1.docstatus = 1""" 
				% (doctype, detail_doctype, '%s'), docname)
			if submitted:
				msgprint(cstr(doctype) + ": " + cstr(submitted[0][0]) 
					+ _(" has already been submitted."), raise_exception=1)

		if check == 'Previous':
			submitted = webnotes.conn.sql("""select name from `tab%s` 
				where docstatus = 1 and name = %s"""% (doctype, '%s'), docname)
			if not submitted:
				msgprint(cstr(doctype) + ": " + cstr(submitted[0][0]) 
					+ _(" not submitted"), raise_exception=1)
