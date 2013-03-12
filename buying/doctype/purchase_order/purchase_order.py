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

from webnotes.utils import cstr, flt
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from buying.utils import get_last_purchase_details

sql = webnotes.conn.sql
	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Purchase Order Item'
		self.fname = 'po_details'
		
	def validate(self):
		super(DocType, self).validate()
		
		self.validate_fiscal_year()

		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])

		# Step 2:=> get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')
		

		# Step 4:=> validate for items
		pc_obj.validate_for_items(self)

		# Get po date
		pc_obj.get_prevdoc_date(self)
		
		# validate_doc
		self.validate_doc(pc_obj)
		
		# Check for stopped status
		self.check_for_stopped_status(pc_obj)
		
		# sub-contracting
		self.validate_for_subcontracting()
		self.update_raw_materials_supplied("po_raw_material_details")
		

	def get_default_schedule_date(self):
		get_obj(dt = 'Purchase Common').get_default_schedule_date(self)
		
	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'PO Date')

	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	# Pull Material Request
	def get_indent_details(self):
		if self.doc.indent_no:
			get_obj('DocType Mapper','Material Request-Purchase Order').dt_map('Material Request','Purchase Order',self.doc.indent_no, self.doc, self.doclist, "[['Material Request','Purchase Order'],['Material Request Item', 'Purchase Order Item']]")
			for d in getlist(self.doclist, 'po_details'):
				if d.item_code and not d.purchase_rate:
					last_purchase_details = get_last_purchase_details(d.item_code, self.doc.name)
					if last_purchase_details:
						conversion_factor = d.conversion_factor or 1.0
						conversion_rate = self.doc.fields.get('conversion_rate') or 1.0
						d.purchase_ref_rate = last_purchase_details['purchase_ref_rate'] * conversion_factor
						d.discount_rate = last_purchase_details['discount_rate']
						d.purchase_rate = last_purchase_details['purchase_rate'] * conversion_factor
						d.import_ref_rate = d.purchase_ref_rate / conversion_rate
						d.import_rate = d.purchase_rate / conversion_rate						
					else:
						d.purchase_ref_rate = d.discount_rate = d.purchase_rate = d.import_ref_rate = d.import_rate = 0.0
						
	def get_supplier_quotation_items(self):
		if self.doc.supplier_quotation:
			get_obj("DocType Mapper", "Supplier Quotation-Purchase Order").dt_map("Supplier Quotation",
				"Purchase Order", self.doc.supplier_quotation, self.doc, self.doclist,
				"""[['Supplier Quotation', 'Purchase Order'],
				['Supplier Quotation Item', 'Purchase Order Item'],
				['Purchase Taxes and Charges', 'Purchase Taxes and Charges']]""")
			self.get_default_schedule_date()
			for d in getlist(self.doclist, 'po_details'):
				if d.prevdoc_detail_docname and not d.schedule_date:
					d.schedule_date = webnotes.conn.get_value("Material Request Item",
							d.prevdoc_detail_docname, "schedule_date")
	
	def get_tc_details(self):
		"""get terms & conditions"""
		return get_obj('Purchase Common').get_tc_details(self)

	def get_last_purchase_rate(self):
		get_obj('Purchase Common').get_last_purchase_rate(self)
		
	def validate_doc(self,pc_obj):
		# Validate values with reference document
		pc_obj.validate_reference_value(obj = self)

	# Check for Stopped status 
	def check_for_stopped_status(self, pc_obj):
		check_list =[]
		for d in getlist(self.doclist, 'po_details'):
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
				check_list.append(d.prevdoc_docname)
				pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

		
	def update_bin(self, is_submit, is_stopped = 0):
		pc_obj = get_obj('Purchase Common')
		for d in getlist(self.doclist, 'po_details'):
			#1. Check if is_stock_item == 'Yes'
			if webnotes.conn.get_value("Item", d.item_code, "is_stock_item") == "Yes":
				# this happens when item is changed from non-stock to stock item
				if not d.warehouse:
					continue
				
				ind_qty, po_qty = 0, flt(d.qty) * flt(d.conversion_factor)
				if is_stopped:
					po_qty = flt(d.qty) > flt(d.received_qty) and \
						flt( flt(flt(d.qty) - flt(d.received_qty))*flt(d.conversion_factor)) or 0 
				
				# No updates in Material Request on Stop / Unstop
				if cstr(d.prevdoc_doctype) == 'Material Request' and not is_stopped:
					# get qty and pending_qty of prevdoc 
					curr_ref_qty = pc_obj.get_qty(d.doctype, 'prevdoc_detail_docname',
					 	d.prevdoc_detail_docname, 'Material Request Item', 
						'Material Request - Purchase Order', self.doc.name)
					max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
					 	flt(curr_ref_qty.split('~~~')[0]), 0
					
					if flt(qty) + flt(po_qty) > flt(max_qty):
						curr_qty = flt(max_qty) - flt(qty)
						# special case as there is no restriction 
						# for Material Request - Purchase Order 
						curr_qty = curr_qty > 0 and curr_qty or 0
					else:
						curr_qty = flt(po_qty)
					
					ind_qty = -flt(curr_qty)

				# Update ordered_qty and indented_qty in bin
				args = {
					"item_code" : d.item_code,
					"ordered_qty" : (is_submit and 1 or -1) * flt(po_qty),
					"indented_qty" : (is_submit and 1 or -1) * flt(ind_qty),
					"posting_date": self.doc.transaction_date
				}
				get_obj("Warehouse", d.warehouse).update_bin(args)
				
	def check_modified_date(self):
		mod_db = sql("select modified from `tabPurchase Order` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception

	def update_status(self, status):
		self.check_modified_date()
		# step 1:=> Set Status
		webnotes.conn.set(self.doc,'status',cstr(status))

		# step 2:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# step 3:=> Acknowledge user
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)))

	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)
		
		# Step 1 :=> Update Previous Doc i.e. update pending_qty and Status accordingly
		purchase_controller.update_prevdoc_detail(self, is_submit = 1)

		# Step 2 :=> Update Bin 
		self.update_bin(is_submit = 1, is_stopped = 0)
		
		# Step 3 :=> Check For Approval Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total)
		
		# Step 5 :=> Update last purchase rate
		purchase_controller.update_last_purchase_rate(self, is_submit = 1)

		# Step 6 :=> Set Status
		webnotes.conn.set(self.doc,'status','Submitted')
	 
	def on_cancel(self):
		pc_obj = get_obj(dt = 'Purchase Common')
		
		# Check if PO status is stopped
		pc_obj.check_for_stopped_status(cstr(self.doc.doctype), cstr(self.doc.name))
		
		self.check_for_stopped_status(pc_obj)
		
		# Check if Purchase Receipt has been submitted against current Purchase Order
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Receipt', docname = self.doc.name, detail_doctype = 'Purchase Receipt Item')

		# Check if Purchase Invoice has been submitted against current Purchase Order
		submitted = sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_order = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		webnotes.conn.set(self.doc,'status','Cancelled')
		pc_obj.update_prevdoc_detail(self,is_submit = 0)
		self.update_bin( is_submit = 0, is_stopped = 0)
		pc_obj.update_last_purchase_rate(self, is_submit = 0)
				
	def on_update(self):
		pass
		
	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)	
	
	def load_default_taxes(self):
		self.doclist = get_obj('Purchase Common').load_default_taxes(self)

	def get_purchase_tax_details(self):
		self.doclist = get_obj('Purchase Common').get_purchase_tax_details(self)
