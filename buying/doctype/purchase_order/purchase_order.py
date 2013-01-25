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

from webnotes.utils import cstr, flt, get_defaults
from webnotes.model.doc import addchild
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from buying.utils import get_last_purchase_details
from setup.utils import get_company_currency

sql = webnotes.conn.sql
	
from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.defaults = get_defaults()
		self.tname = 'Purchase Order Item'
		self.fname = 'po_details'
		
		# Validate
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
		

	def get_default_schedule_date(self):
		get_obj(dt = 'Purchase Common').get_default_schedule_date(self)
		
	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'PO Date')

	# get available qty at warehouse
	def get_bin_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_bin_details(arg)

	# Pull Purchase Request
	def get_indent_details(self):
		if self.doc.indent_no:
			get_obj('DocType Mapper','Purchase Request-Purchase Order').dt_map('Purchase Request','Purchase Order',self.doc.indent_no, self.doc, self.doclist, "[['Purchase Request','Purchase Order'],['Purchase Request Item', 'Purchase Order Item']]")
			pcomm = get_obj('Purchase Common')
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
					d.schedule_date = webnotes.conn.get_value("Purchase Request Item",
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
				ind_qty, po_qty = 0, flt(d.qty) * flt(d.conversion_factor)
				if is_stopped:
					po_qty = flt(d.qty) > flt(d.received_qty) and \
						flt( flt(flt(d.qty) - flt(d.received_qty))*flt(d.conversion_factor)) or 0 
				
				# No updates in Purchase Request on Stop / Unstop
				if cstr(d.prevdoc_doctype) == 'Purchase Request' and not is_stopped:
					# get qty and pending_qty of prevdoc 
					curr_ref_qty = pc_obj.get_qty(d.doctype, 'prevdoc_detail_docname',
					 	d.prevdoc_detail_docname, 'Purchase Request Item', 
						'Purchase Request - Purchase Order', self.doc.name)
					max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), \
					 	flt(curr_ref_qty.split('~~~')[0]), 0
					
					if flt(qty) + flt(po_qty) > flt(max_qty):
						curr_qty = flt(max_qty) - flt(qty)
						# special case as there is no restriction 
						# for Purchase Request - Purchase Order 
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

	# On Close
	#-------------------------------------------------------------------------------------------------
	def update_status(self, status):
		self.check_modified_date()
		# step 1:=> Set Status
		webnotes.conn.set(self.doc,'status',cstr(status))

		# step 2:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# step 3:=> Acknowledge user
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)))


	# On Submit
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
	 
	# On Cancel
	# -------------------------------------------------------------------------------------------------------
	def on_cancel(self):
		pc_obj = get_obj(dt = 'Purchase Common')
		
		# 1.Check if PO status is stopped
		pc_obj.check_for_stopped_status(cstr(self.doc.doctype), cstr(self.doc.name))
		
		self.check_for_stopped_status(pc_obj)
		
		# 2.Check if Purchase Receipt has been submitted against current Purchase Order
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Receipt', docname = self.doc.name, detail_doctype = 'Purchase Receipt Item')

		# 3.Check if Purchase Invoice has been submitted against current Purchase Order
		#pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Invoice', docname = self.doc.name, detail_doctype = 'Purchase Invoice Item')
		
		submitted = sql("select t1.name from `tabPurchase Invoice` t1,`tabPurchase Invoice Item` t2 where t1.name = t2.parent and t2.purchase_order = '%s' and t1.docstatus = 1" % self.doc.name)
		if submitted:
			msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
			raise Exception

		# 4.Set Status as Cancelled
		webnotes.conn.set(self.doc,'status','Cancelled')

		# 5.Update Purchase Requests Pending Qty and accordingly it's Status 
		pc_obj.update_prevdoc_detail(self,is_submit = 0)
		
		# 6.Update Bin	
		self.update_bin( is_submit = 0, is_stopped = 0)
		
		# Step 7 :=> Update last purchase rate 
		pc_obj.update_last_purchase_rate(self, is_submit = 0)
		
#----------- code for Sub-contracted Items -------------------
	#--------check for sub-contracted items and accordingly update PO raw material detail table--------
	def update_rw_material_detail(self):
		for d in getlist(self.doclist,'po_details'):
			item_det = sql("select is_sub_contracted_item, is_purchase_item from `tabItem` where name = '%s'"%(d.item_code))
			
			if item_det[0][0] == 'Yes':
				if item_det[0][1] == 'Yes':
					if not self.doc.is_subcontracted:
						msgprint("Please enter whether purchase order to be made for subcontracting or for purchasing in 'Is Subcontracted' field .")
						raise Exception
					if self.doc.is_subcontracted == 'Yes':
						self.add_bom(d)
					else:
						self.doclist = self.doc.clear_table(self.doclist,'po_raw_material_details',1)
						self.doc.save()
				elif item_det[0][1] == 'No':
					self.add_bom(d)
				
			self.delete_irrelevant_raw_material()
			#---------------calculate amt in	Purchase Order Item Supplied-------------
			self.calculate_amount(d)
			
	def add_bom(self, d):
		#----- fetching default bom from Bill of Materials instead of Item Master --
		bom_det = sql("""select t1.item, t2.item_code, t2.qty_consumed_per_unit, 
			t2.moving_avg_rate, t2.value_as_per_mar, t2.stock_uom, t2.name, t2.parent 
			from `tabBOM` t1, `tabBOM Item` t2 
			where t2.parent = t1.name and t1.item = %s 
				and ifnull(t1.is_default,0) = 1 and t1.docstatus = 1""", (d.item_code,))
		
		if not bom_det:
			msgprint("No default BOM exists for item: %s" % d.item_code)
			raise Exception
		else:
			#-------------- add child function--------------------
			chgd_rqd_qty = []
			for i in bom_det:
				if i and not sql("select name from `tabPurchase Order Item Supplied` where reference_name = '%s' and bom_detail_no = '%s' and parent = '%s' " %(d.name, i[6], self.doc.name)):

					rm_child = addchild(self.doc, 'po_raw_material_details', 'Purchase Order Item Supplied', self.doclist)

					rm_child.reference_name = d.name
					rm_child.bom_detail_no = i and i[6] or ''
					rm_child.main_item_code = i and i[0] or ''
					rm_child.rm_item_code = i and i[1] or ''
					rm_child.stock_uom = i and i[5] or ''
					rm_child.rate = i and flt(i[3]) or flt(i[4])
					rm_child.conversion_factor = d.conversion_factor
					rm_child.required_qty = flt(i	and flt(i[2]) or 0) * flt(d.qty) * flt(d.conversion_factor)
					rm_child.amount = flt(flt(rm_child.consumed_qty)*flt(rm_child.rate))
					rm_child.save()
					chgd_rqd_qty.append(cstr(i[1]))
				else:
					act_qty = flt(i	and flt(i[2]) or 0) * flt(d.qty) * flt(d.conversion_factor)
					for po_rmd in getlist(self.doclist, 'po_raw_material_details'):
						if i and i[6] == po_rmd.bom_detail_no and (flt(act_qty) != flt(po_rmd.required_qty) or i[1] != po_rmd.rm_item_code):
							chgd_rqd_qty.append(cstr(i[1]))
							po_rmd.main_item_code = i[0]
							po_rmd.rm_item_code = i[1]
							po_rmd.stock_uom = i[5]
							po_rmd.required_qty = flt(act_qty)
							po_rmd.rate = i and flt(i[3]) or flt(i[4])
							po_rmd.amount = flt(flt(po_rmd.consumed_qty)*flt(po_rmd.rate))
							

	# Delete irrelevant raw material from PR Raw material details
	#--------------------------------------------------------------	
	def delete_irrelevant_raw_material(self):
		for d in getlist(self.doclist,'po_raw_material_details'):
			if not sql("select name from `tabPurchase Order Item` where name = '%s' and parent = '%s'and item_code = '%s'" % (d.reference_name, self.doc.name, d.main_item_code)):
				d.parent = 'old_par:'+self.doc.name
				d.save()
		
	def calculate_amount(self, d):
		amt = 0
		for i in getlist(self.doclist,'po_raw_material_details'):
			
			if(i.reference_name == d.name):
				i.amount = flt(i.required_qty)* flt(i.rate)
				amt += i.amount
		d.rm_supp_cost = amt

	# On Update
	# ----------------------------------------------------------------------------------------------------		
	def on_update(self):
		self.update_rw_material_detail()
		

	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)	
	
	def load_default_taxes(self):
		self.doclist = get_obj('Purchase Common').load_default_taxes(self)

	def get_purchase_tax_details(self):
		self.doclist = get_obj('Purchase Common').get_purchase_tax_details(self)
