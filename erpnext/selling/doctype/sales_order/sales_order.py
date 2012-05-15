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
from webnotes.model import db_exists
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
		self.tname = 'Sales Order Item'
		self.fname = 'sales_order_details'
		self.person_tname = 'Target Detail'
		self.partner_tname = 'Partner Target Detail'
		self.territory_tname = 'Territory Target Detail'

# Autoname
# ===============
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')

		
# DOCTYPE TRIGGER FUNCTIONS
# =============================
	# Pull Quotation Items
	# -----------------------
	def pull_quotation_details(self):
		self.doc.clear_table(self.doclist, 'other_charges')
		self.doc.clear_table(self.doclist, 'sales_order_details')
		self.doc.clear_table(self.doclist, 'sales_team')
		self.doc.clear_table(self.doclist, 'tc_details')
		if self.doc.quotation_no:				
			get_obj('DocType Mapper', 'Quotation-Sales Order').dt_map('Quotation', 'Sales Order', self.doc.quotation_no, self.doc, self.doclist, "[['Quotation', 'Sales Order'],['Quotation Item', 'Sales Order Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team'],['TC Detail','TC Detail']]")			
		else:
			msgprint("Please select Quotation whose details need to pull")		

		return cstr(self.doc.quotation_no)
	
	#pull project customer
	#-------------------------
	def pull_project_customer(self):
		res = sql("select customer from `tabProject` where name = '%s'"%self.doc.project_name)
		if res:
			get_obj('DocType Mapper', 'Project-Sales Order').dt_map('Project', 'Sales Order', self.doc.project_name, self.doc, self.doclist, "[['Project', 'Sales Order']]")
			
	
	# Get contact person details based on customer selected
	# ------------------------------------------------------
	def get_contact_details(self):
		get_obj('Sales Common').get_contact_details(self,0)

	# Get Commission rate of Sales Partner
	# -------------------------------------
	def get_comm_rate(self, sales_partner):
		return get_obj('Sales Common').get_comm_rate(sales_partner, self)


# SALES ORDER DETAILS TRIGGER FUNCTIONS
# ================================================================================
	# Get Item Details
	# ----------------
	def get_item_details(self, args=None):
		import json
		args = args and json.loads(args) or {}
		if args.get('item_code'):
			return get_obj('Sales Common').get_item_details(args, self)
		else:
			obj = get_obj('Sales Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					arg = {'item_code':doc.fields.get('item_code'), 'income_account':doc.fields.get('income_account'), 
						'cost_center': doc.fields.get('cost_center'), 'warehouse': doc.fields.get('warehouse')};
					ret = obj.get_item_defaults(arg)
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]					


	# Re-calculates Basic Rate & amount based on Price List Selected
	# --------------------------------------------------------------
	def get_adj_percent(self, arg=''):
		get_obj('Sales Common').get_adj_percent(self)



	# Get projected qty of item based on warehouse selected
	# -----------------------------------------------------
	def get_available_qty(self,args):
		args = eval(args)
		tot_avail_qty = sql("select projected_qty, actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], args['warehouse']), as_dict=1)
		ret = {
			 'projected_qty' : tot_avail_qty and flt(tot_avail_qty[0]['projected_qty']) or 0,
			 'actual_qty' : tot_avail_qty and flt(tot_avail_qty[0]['actual_qty']) or 0
		}
		return ret
	
# OTHER CHARGES TRIGGER FUNCTIONS
# ====================================================================================
	
	# Get Tax rate if account type is TAX
	# ------------------------------------
	def get_rate(self,arg):
		return get_obj('Sales Common').get_rate(arg)

	# Load Default Charges
	# ----------------------------------------------------------
	def load_default_taxes(self):
		return get_obj('Sales Common').load_default_taxes(self)

	# Pull details from other charges master (Get Sales Taxes and Charges Master)
	# ----------------------------------------------------------
	def get_other_charges(self):
		return get_obj('Sales Common').get_other_charges(self)
 
 
# GET TERMS & CONDITIONS
# =====================================================================================
	def get_tc_details(self):
		return get_obj('Sales Common').get_tc_details(self)

#check if maintenance schedule already generated
#============================================
	def check_maintenance_schedule(self):
		nm = sql("select t1.name from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1", self.doc.name)
		nm = nm and nm[0][0] or ''
		
		if not nm:
			return 'No'

#check if maintenance visit already generated
#============================================
	def check_maintenance_visit(self):
		nm = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1 and t1.completion_status='Fully Completed'", self.doc.name)
		nm = nm and nm[0][0] or ''
		
		if not nm:
			return 'No'

# VALIDATE
# =====================================================================================
	# Fiscal Year Validation
	# ----------------------
	def validate_fiscal_year(self):
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'Sales Order Date')
	
	# Validate values with reference document
	#----------------------------------------
	def validate_reference_value(self):
		get_obj('DocType Mapper', 'Quotation-Sales Order', with_children = 1).validate_reference_value(self, self.doc.name)

	# Validate Mandatory
	# -------------------
	def validate_mandatory(self):
		# validate transaction date v/s delivery date
		if self.doc.delivery_date:
			if getdate(self.doc.transaction_date) > getdate(self.doc.delivery_date):
				msgprint("Expected Delivery Date cannot be before Sales Order Date")
				raise Exception

	# Validate P.O Date
	# ------------------
	def validate_po_date(self):
		# validate p.o date v/s delivery date
		if self.doc.po_date and self.doc.delivery_date and getdate(self.doc.po_date) > getdate(self.doc.delivery_date):
			msgprint("Expected Delivery Date cannot be before Purchase Order Date")
			raise Exception	
		# amendment date is necessary if document is amended
		if self.doc.amended_from and not self.doc.amendment_date:
			msgprint("Please Enter Amendment Date")
			raise Exception
	
	# Validations of Details Table
	# -----------------------------
	def validate_for_items(self):
		check_list,flag = [],0
		chk_dupl_itm = []
		# Sales Order Items Validations
		for d in getlist(self.doclist, 'sales_order_details'):
			if cstr(self.doc.quotation_no) == cstr(d.prevdoc_docname):
				flag = 1
			if d.prevdoc_docname:
				if self.doc.quotation_date and getdate(self.doc.quotation_date) > getdate(self.doc.transaction_date):
					msgprint("Sales Order Date cannot be before Quotation Date")
					raise Exception
				# validates whether quotation no in doctype and in table is same
				if not cstr(d.prevdoc_docname) == cstr(self.doc.quotation_no):
					msgprint("Items in table does not belong to the Quotation No mentioned.")
					raise Exception

			# validates whether item is not entered twice
			e = [d.item_code, d.description, d.reserved_warehouse, d.prevdoc_docname or '']
			f = [d.item_code, d.description]

			#check item is stock item
			st_itm = sql("select is_stock_item from `tabItem` where name = '%s'"%d.item_code)

			if st_itm and st_itm[0][0] == 'Yes':
				if e in check_list:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					check_list.append(e)
			elif st_itm and st_itm[0][0]== 'No':
				if f in chk_dupl_itm:
					msgprint("Item %s has been entered twice." % d.item_code)
				else:
					chk_dupl_itm.append(f)

			# used for production plan
			d.transaction_date = self.doc.transaction_date
			d.delivery_date = self.doc.delivery_date

			# gets total projected qty of item in warehouse selected (this case arises when warehouse is selected b4 item)
			tot_avail_qty = sql("select projected_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code,d.reserved_warehouse))
			d.projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0
		
		if flag == 0:
			msgprint("There are no items of the quotation selected.")
			raise Exception

	# validate sales/ service item against order type
	#----------------------------------------------------
	def validate_sales_mntc_item(self):
		if self.doc.order_type == 'Maintenance':
			item_field = 'is_service_item'
			order_type = 'Maintenance Order'
			item_type = 'service item'
		else :
			item_field = 'is_sales_item'
			order_type = 'Sales Order'
			item_type = 'sales item'
		
		for d in getlist(self.doclist, 'sales_order_details'):
			res = sql("select %s from `tabItem` where name='%s'"% (item_field,d.item_code))
			res = res and res[0][0] or 'No'
			
			if res == 'No':
				msgprint("You can not select non "+item_type+" "+d.item_code+" in "+order_type)
				raise Exception
	
	# validate sales/ maintenance quotation against order type
	#------------------------------------------------------------------
	def validate_sales_mntc_quotation(self):
		for d in getlist(self.doclist, 'sales_order_details'):
			if d.prevdoc_docname:
				res = sql("select order_type from `tabQuotation` where name=%s", (d.prevdoc_docname))
				res = res and res[0][0] or ''
				
				if self.doc.order_type== 'Maintenance' and res != 'Maintenance':
					msgprint("You can not select non Maintenance Quotation against Maintenance Order")
					raise Exception
				elif self.doc.order_type != 'Maintenance' and res == 'Maintenance':
					msgprint("You can not select non Sales Quotation against Sales Order")
					raise Exception

	#do not allow sales item/quotation in maintenance order and service item/quotation in sales order
	#-----------------------------------------------------------------------------------------------
	def validate_order_type(self):
		#validate delivery date
		if self.doc.order_type != 'Maintenance' and not self.doc.delivery_date:
			msgprint("Please enter 'Expected Delivery Date'")
			raise Exception
		
		self.validate_sales_mntc_quotation()
		self.validate_sales_mntc_item()

	#check for does customer belong to same project as entered..
	#-------------------------------------------------------------------------------------------------
	def validate_proj_cust(self):
		if self.doc.project_name and self.doc.customer_name:
			res = sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in project - %s."%(self.doc.customer,self.doc.project_name,self.doc.project_name))
				raise Exception
			 

	# Validate
	# ---------
	def validate(self):
		self.validate_fiscal_year()
		self.validate_order_type()
		self.validate_mandatory()
		self.validate_proj_cust()
		self.validate_po_date()
		#self.validate_reference_value()
		self.validate_for_items()
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.check_conversion_rate(self)

				# verify whether rate is not greater than max_discount
		sales_com_obj.validate_max_discount(self,'sales_order_details')
				# this is to verify that the allocated % of sales persons is 100%
		sales_com_obj.get_allocated_sum(self)
		sales_com_obj.make_packing_list(self,'sales_order_details')
		
				# get total in words
		dcc = TransactionBase().get_company_currency(self.doc.company)		
		self.doc.in_words = sales_com_obj.get_total_in_words(dcc, self.doc.rounded_total)
		self.doc.in_words_export = sales_com_obj.get_total_in_words(self.doc.currency, self.doc.rounded_total_export)
		
		# set SO status
		self.doc.status='Draft'
		if not self.doc.billing_status: self.doc.billing_status = 'Not Billed'
		if not self.doc.delivery_status: self.doc.delivery_status = 'Not Delivered'
		

# ON SUBMIT
# ===============================================================================================
	# Checks Quotation Status
	# ------------------------
	def check_prev_docstatus(self):
		for d in getlist(self.doclist, 'sales_order_details'):
			cancel_quo = sql("select name from `tabQuotation` where docstatus = 2 and name = '%s'" % d.prevdoc_docname)
			if cancel_quo:
				msgprint("Quotation :" + cstr(cancel_quo[0][0]) + " is already cancelled !")
				raise Exception , "Validation Error. "
	
	def update_enquiry_status(self, prevdoc, flag):
		enq = sql("select t2.prevdoc_docname from `tabQuotation` t1, `tabQuotation Item` t2 where t2.parent = t1.name and t1.name=%s", prevdoc)
		if enq:
			sql("update `tabOpportunity` set status = %s where name=%s",(flag,enq[0][0]))

	#update status of quotation, enquiry
	#----------------------------------------
	def update_prevdoc_status(self, flag):
		for d in getlist(self.doclist, 'sales_order_details'):
			if d.prevdoc_docname:
				if flag=='submit':
					sql("update `tabQuotation` set status = 'Order Confirmed' where name=%s",d.prevdoc_docname)
					
					#update enquiry
					self.update_enquiry_status(d.prevdoc_docname, 'Order Confirmed')
				elif flag == 'cancel':
					chk = sql("select t1.name from `tabSales Order` t1, `tabSales Order Item` t2 where t2.parent = t1.name and t2.prevdoc_docname=%s and t1.name!=%s and t1.docstatus=1", (d.prevdoc_docname,self.doc.name))
					if not chk:
						sql("update `tabQuotation` set status = 'Submitted' where name=%s",d.prevdoc_docname)
						
						#update enquiry
						self.update_enquiry_status(d.prevdoc_docname, 'Quotation Sent')
	
	# Submit
	# -------
	def on_submit(self):
		self.check_prev_docstatus()		
		self.update_stock_ledger(update_stock = 1)
		self.set_sms_msg(1)
		# update customer's last sales order no.
		update_customer = sql("update `tabCustomer` set last_sales_order = '%s', modified = '%s' where name = '%s'" %(self.doc.name, self.doc.modified, self.doc.customer))
		get_obj('Sales Common').check_credit(self,self.doc.grand_total)
		
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.grand_total, self)
		
		#update prevdoc status
		self.update_prevdoc_status('submit')
		# set SO status
		set(self.doc, 'status', 'Submitted')
	
 
# ON CANCEL
# ===============================================================================================
	def on_cancel(self):
		# Cannot cancel stopped SO
		if self.doc.status == 'Stopped':
			msgprint("Sales Order : '%s' cannot be cancelled as it is Stopped. Unstop it for any further transactions" %(self.doc.name))
			raise Exception
		self.check_nextdoc_docstatus()
		self.update_stock_ledger(update_stock = -1)
		self.set_sms_msg()
		
		#update prevdoc status
		self.update_prevdoc_status('cancel')
		
		# ::::::::: SET SO STATUS ::::::::::
		set(self.doc, 'status', 'Cancelled')
		
	# CHECK NEXT DOCSTATUS
	# does not allow to cancel document if DN or RV made against it is SUBMITTED 
	# ----------------------------------------------------------------------------
	def check_nextdoc_docstatus(self):
		# Checks Delivery Note
		submit_dn = sql("select t1.name from `tabDelivery Note` t1,`tabDelivery Note Item` t2 where t1.name = t2.parent and t2.prevdoc_docname = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_dn:
			msgprint("Delivery Note : " + cstr(submit_dn[0][0]) + " has been submitted against " + cstr(self.doc.doctype) + ". Please cancel Delivery Note : " + cstr(submit_dn[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
		# Checks Sales Invoice
		submit_rv = sql("select t1.name from `tabSales Invoice` t1,`tabSales Invoice Item` t2 where t1.name = t2.parent and t2.sales_order = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Sales Invoice : " + cstr(submit_rv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Sales Invoice : "+ cstr(submit_rv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
		#check maintenance schedule
		submit_ms = sql("select t1.name from `tabMaintenance Schedule` t1, `tabMaintenance Schedule Item` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_ms:
			msgprint("Maintenance Schedule : " + cstr(submit_ms[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Schedule : "+ cstr(submit_ms[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)
		submit_mv = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent=t1.name and t2.prevdoc_docname = %s and t1.docstatus = 1",self.doc.name)
		if submit_mv:
			msgprint("Maintenance Visit : " + cstr(submit_mv[0][0]) + " has already been submitted against " +cstr(self.doc.doctype)+ ". Please cancel Maintenance Visit : " + cstr(submit_mv[0][0]) + " first and then cancel "+ cstr(self.doc.doctype), raise_exception = 1)


	def check_modified_date(self):
		mod_db = sql("select modified from `tabSales Order` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception

	# STOP SALES ORDER
	# ==============================================================================================			
	# Stops Sales Order & no more transactions will be created against this Sales Order
	def stop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(update_stock = -1,clear = 1)
		# ::::::::: SET SO STATUS ::::::::::
		set(self.doc, 'status', 'Stopped')
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been Stopped. To make transactions against this Sales Order you need to Unstop it.")

	# UNSTOP SALES ORDER
	# ==============================================================================================			
	# Unstops Sales Order & now transactions can be continued against this Sales Order
	def unstop_sales_order(self):
		self.check_modified_date()
		self.update_stock_ledger(update_stock = 1,clear = 1)
		# ::::::::: SET SO STATUS ::::::::::
		set(self.doc, 'status', 'Submitted')
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been Unstopped.")

	# UPDATE STOCK LEDGER
	# ===============================================================================================
	def update_stock_ledger(self, update_stock, clear = 0):
		for d in self.get_item_list(clear):
			stock_item = sql("SELECT is_stock_item FROM tabItem where name = '%s'"%(d[1]),as_dict = 1)			 # stock ledger will be updated only if it is a stock item
			if stock_item and stock_item[0]['is_stock_item'] == "Yes":
				if not d[0]:
					msgprint("Message: Please enter Reserved Warehouse for item %s as it is stock item."% d[1])
					raise Exception
				bin = get_obj('Warehouse', d[0]).update_bin( 0, flt(update_stock) * flt(d[2]), 0, 0, 0, d[1], self.doc.transaction_date,doc_type=self.doc.doctype,doc_name=self.doc.name, is_amended = (self.doc.amended_from and 'Yes' or 'No'))
	
	# Gets Items from packing list
	#=================================
	def get_item_list(self, clear):
		return get_obj('Sales Common').get_item_list( self, clear)
		
	# SET MESSAGE FOR SMS
	#======================
	def set_sms_msg(self, is_submitted = 0):
		if is_submitted:
			if not self.doc.amended_from:
				msg = 'Sales Order: '+self.doc.name+' has been made against PO no: '+cstr(self.doc.po_no)
				set(self.doc, 'message', msg)
			else:
				msg = 'Sales Order has been amended. New SO no:'+self.doc.name
				set(self.doc, 'message', msg)
		else:
			msg = 'Sales Order: '+self.doc.name+' has been cancelled.'
			set(self.doc, 'message', msg)
		
	# SEND SMS
	# =========
	def send_sms(self):
		if not self.doc.customer_mobile_no:
			msgprint("Please enter customer mobile no")
		elif not self.doc.message:
			msgprint("Please enter the message you want to send")
		else:
			msgprint(get_obj("SMS Control", "SMS Control").send_sms([self.doc.customer_mobile_no,], self.doc.message))

	# on update
	def on_update(self):
		pass

