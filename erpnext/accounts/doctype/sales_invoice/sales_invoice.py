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

from webnotes.utils import add_days, add_months, add_years, cint, cstr,date_diff, default_fields, flt, fmt_money, formatdate, generate_hash,getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common,month_name, now, nowdate, replace_newlines, sendmail, set_default,str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
session = webnotes.session

# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.log = []
		self.tname = 'Sales Invoice Item'
		self.fname = 'entries'


	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')



# ********************************* Trigger Functions ******************************

	#Set retail related fields from pos settings
	#-------------------------------------------------------------------------
	def set_pos_fields(self):
		pos = webnotes.conn.sql("select * from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)
		if not pos:
			pos = webnotes.conn.sql("select * from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)
		if pos:
			val = webnotes.conn.sql("select name from `tabAccount` where name = %s and docstatus != 2", (cstr(self.doc.customer) + " - " + self.get_company_abbr()))
			val = val and val[0][0] or ''
			if not val: val = pos and pos[0]['customer_account'] or ''
			if not self.doc.debit_to:
				webnotes.conn.set(self.doc,'debit_to',val)
			
			lst = ['territory','naming_series','currency','charge','letter_head','tc_name','price_list_name','company','select_print_heading','cash_bank_account']
				
			for i in lst:
				val = pos and pos[0][i] or ''
				self.doc.fields[i] = val
			self.set_pos_item_values()
			
			val = pos and flt(pos[0]['conversion_rate']) or 0	
			self.doc.conversion_rate = val

			#fetch terms	
			if self.doc.tc_name:	 self.get_tc_details()
			
			#fetch charges
			if self.doc.charge:		self.get_other_charges()


	# Set default values related to pos for previously created sales invoice.
	# -------------------------------------------------------------------------- 
	def set_pos_item_values(self):
		if cint(self.doc.is_pos) ==1:
			dtl = webnotes.conn.sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)
			if not dtl:
				dtl = webnotes.conn.sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)
			for d in getlist(self.doclist,'entries'):
				# overwrite if mentioned in item
				item = webnotes.conn.sql("select default_income_account, default_sales_cost_center, default_warehouse from tabItem where name = '%s'" %(d.item_code), as_dict=1)
				d.income_account = item and item[0]['default_income_account'] or dtl and dtl[0]['income_account'] or d.income_account
				d.cost_center = item and item[0]['default_sales_cost_center'] or dtl and dtl[0]['cost_center'] or d.cost_center
				d.warehouse = item and item[0]['default_warehouse'] or dtl and dtl[0]['warehouse'] or d.warehouse


			
	# Get Account Head to which amount needs to be Debited based on Customer
	# ----------------------------------------------------------------------
	def get_customer_account(self):
		if not self.doc.company:
			msgprint("Please select company first and re-select the customer after doing so", raise_exception=1)
			
		acc_head = webnotes.conn.sql("""select name from `tabAccount` 
			where (name = %s or (master_name = %s and master_type = 'customer')) and docstatus != 2""", 
			(cstr(self.doc.customer) + " - " + self.get_company_abbr(),self.doc.customer))
			
		if acc_head and acc_head[0][0]:
			return acc_head[0][0]
		else:
			msgprint("%s does not have an Account Head in %s. You must first create it from the Customer Master" % (self.doc.customer, self.doc.company))

	def get_debit_to(self):
		acc_head = self.get_customer_account()
		return acc_head and {'debit_to' : acc_head} or {}



	# Set Due Date = Posting Date + Credit Days
	# -----------------------------------------
	def get_cust_and_due_date(self):
		credit_days = 0
		if self.doc.debit_to:
			credit_days = webnotes.conn.sql("select credit_days from `tabAccount` where name='%s' and docstatus != 2" % self.doc.debit_to)
			credit_days = credit_days and cint(credit_days[0][0]) or 0
		if self.doc.company and not credit_days:
			credit_days = webnotes.conn.sql("select credit_days from `tabCompany` where name='%s'" % self.doc.company)
			credit_days = credit_days and cint(credit_days[0][0]) or 0
		# Customer has higher priority than company
		# i.e.if not entered in customer will take credit days from company
		self.doc.due_date = add_days(cstr(self.doc.posting_date), credit_days)
		
		if self.doc.debit_to:
			self.doc.customer = webnotes.conn.get_value('Account',self.doc.debit_to,'master_name')


	# Pull Details of Delivery Note or Sales Order Selected
	# ------------------------------------------------------
	def pull_details(self):
		# Delivery Note
		if self.doc.delivery_note_main:
			self.validate_prev_docname('delivery note')
			self.doclist = self.doc.clear_table(self.doclist,'other_charges')			
			self.doclist = get_obj('DocType Mapper', 'Delivery Note-Sales Invoice').dt_map('Delivery Note', 'Sales Invoice', self.doc.delivery_note_main, self.doc, self.doclist, "[['Delivery Note', 'Sales Invoice'],['Delivery Note Item', 'Sales Invoice Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]")			
			self.get_income_account('entries')
		# Sales Order
		elif self.doc.sales_order_main:
			self.validate_prev_docname('sales order')
			self.doclist = self.doc.clear_table(self.doclist,'other_charges')
			get_obj('DocType Mapper', 'Sales Order-Sales Invoice').dt_map('Sales Order', 'Sales Invoice', self.doc.sales_order_main, self.doc, self.doclist, "[['Sales Order', 'Sales Invoice'],['Sales Order Item', 'Sales Invoice Item'],['Sales Taxes and Charges','Sales Taxes and Charges'], ['Sales Team', 'Sales Team']]")
			self.get_income_account('entries')
			
		ret = self.get_debit_to()
		self.doc.debit_to = ret.get('debit_to')
					
	# onload pull income account
	# --------------------------
	def load_default_accounts(self):
		"""
			Loads default accounts from items, customer when called from mapper
		"""
		self.get_income_account('entries')
		
	def get_income_account(self,doctype):		
		for d in getlist(self.doclist, doctype):			
			if d.item_code:
				item = webnotes.conn.sql("select default_income_account, default_sales_cost_center from tabItem where name = '%s'" %(d.item_code), as_dict=1)
				d.income_account = item and item[0]['default_income_account'] or ''
				d.cost_center = item and item[0]['default_sales_cost_center'] or ''				

	# Item Details
	# -------------
	def get_item_details(self, args=None):
		import json
		args = args and json.loads(args) or {}
		if args.get('item_code'):
			ret = get_obj('Sales Common').get_item_details(args, self)
			return self.get_pos_details(args, ret)
		else:
			obj = get_obj('Sales Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					arg = {'item_code':doc.fields.get('item_code'), 'income_account':doc.fields.get('income_account'), 
						'cost_center': doc.fields.get('cost_center'), 'warehouse': doc.fields.get('warehouse')};

					ret = self.get_pos_details(arg)
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]		


	def get_pos_details(self, args, ret = {}):
		if args['item_code'] and cint(self.doc.is_pos) == 1:
			dtl = webnotes.conn.sql("select income_account, warehouse, cost_center from `tabPOS Setting` where user = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)				 
			if not dtl:
				dtl = webnotes.conn.sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)

			item = webnotes.conn.sql("select default_income_account, default_sales_cost_center, default_warehouse from tabItem where name = '%s'" %(args['item_code']), as_dict=1)

			ret['income_account'] = item and item[0].get('default_income_account') \
				or (dtl and dtl[0].get('income_account') or args.get('income_account'))

			ret['cost_center'] = item and item[0].get('default_sales_cost_center') \
				or (dtl and dtl[0].get('cost_center') or args.get('cost_center'))
			
			ret['warehouse'] = item and item[0].get('default_warehouse') \
				or (dtl and dtl[0].get('warehouse') or args.get('warehouse'))

			if ret['warehouse']:
				actual_qty = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], ret['warehouse']))
				ret['actual_qty']= actual_qty and flt(actual_qty[0][0]) or 0
		return ret

	def get_barcode_details(self, barcode):
		return get_obj('Sales Common').get_barcode_details(barcode)


	# Fetch ref rate from item master as per selected price list
	def get_adj_percent(self, arg=''):
		get_obj('Sales Common').get_adj_percent(self)


	# Get tax rate if account type is tax
	# ------------------------------------
	def get_rate(self,arg):
		get_obj('Sales Common').get_rate(arg)
		
		
	# Get Commission rate of Sales Partner
	# -------------------------------------
	def get_comm_rate(self, sales_partner):
		return get_obj('Sales Common').get_comm_rate(sales_partner, self)	
	
 
	# GET TERMS & CONDITIONS
	# -------------------------------------
	def get_tc_details(self):
		return get_obj('Sales Common').get_tc_details(self)

	# Load Default Charges
	# ----------------------------------------------------------
	def load_default_taxes(self):
		self.doclist = get_obj('Sales Common').load_default_taxes(self)

	# Get Sales Taxes and Charges Master Details
	# --------------------------
	def get_other_charges(self):
		self.doclist = get_obj('Sales Common').get_other_charges(self)

	# Get Advances
	# -------------
	def get_advances(self):
		self.doclist = get_obj('GL Control').get_advances(self, self.doc.debit_to, 'Sales Invoice Advance', 'advance_adjustment_details', 'credit')

	#pull project customer
	#-------------------------
	def pull_project_customer(self):
		res = webnotes.conn.sql("select customer from `tabProject` where name = '%s'"%self.doc.project_name)
		if res:
			get_obj('DocType Mapper', 'Project-Sales Invoice').dt_map('Project', 'Sales Invoice', self.doc.project_name, self.doc, self.doclist, "[['Project', 'Sales Invoice']]")

# ********************************** Server Utility Functions ******************************
	
	# Get Company Abbr.
	# ------------------
	def get_company_abbr(self):
		return webnotes.conn.sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
		
	
	# Check whether sales order / delivery note items already pulled
	#----------------------------------------------------------------
	def validate_prev_docname(self,doctype):
		for d in getlist(self.doclist, 'entries'): 
			if doctype == 'delivery note' and self.doc.delivery_note_main == d.delivery_note:
				msgprint(cstr(self.doc.delivery_note_main) + " delivery note details have already been pulled.")
				raise Exception , "Validation Error. Delivery note details have already been pulled."
			elif doctype == 'sales order' and self.doc.sales_order_main == d.sales_order and not d.delivery_note:
				msgprint(cstr(self.doc.sales_order_main) + " sales order details have already been pulled.")
				raise Exception , "Validation Error. Sales order details have already been pulled."


	#-----------------------------------------------------------------
	def update_against_document_in_jv(self):
		"""
			Links invoice and advance voucher:
				1. cancel advance voucher
				2. split into multiple rows if partially adjusted, assign against voucher
				3. submit advance voucher
		"""
		
		lst = []
		for d in getlist(self.doclist, 'advance_adjustment_details'):
			if flt(d.allocated_amount) > 0:
				args = {
					'voucher_no' : d.journal_voucher, 
					'voucher_detail_no' : d.jv_detail_no, 
					'against_voucher_type' : 'Sales Invoice', 
					'against_voucher'  : self.doc.name,
					'account' : self.doc.debit_to, 
					'is_advance' : 'Yes', 
					'dr_or_cr' : 'credit', 
					'unadjusted_amt' : flt(d.advance_amount),
					'allocated_amt' : flt(d.allocated_amount)
				}
				lst.append(args)
		
		if lst:
			get_obj('GL Control').reconcile_against_document(lst)
	
	
	# ------------------------------------------------------------------------
	def validate_customer(self):
		"""
			Validate customer name with SO and DN
		"""
		for d in getlist(self.doclist,'entries'):
			dt = d.delivery_note and 'Delivery Note' or d.sales_order and 'Sales Order' or ''
			if dt:
				dt_no = d.delivery_note or d.sales_order
				cust = webnotes.conn.sql("select customer from `tab%s` where name = %s" % (dt, '%s'), dt_no)
				if cust and cstr(cust[0][0]) != cstr(self.doc.customer):
					msgprint("Customer %s does not match with customer of %s: %s." %(self.doc.customer, dt, dt_no), raise_exception=1)
			

	# Validates Debit To Account and Customer Matches
	# ------------------------------------------------
	def validate_debit_to_acc(self):
		if self.doc.customer and self.doc.debit_to and not cint(self.doc.is_pos):
			acc_head = webnotes.conn.sql("select master_name from `tabAccount` where name = %s and docstatus != 2", self.doc.debit_to)
			
			if (acc_head and cstr(acc_head[0][0]) != cstr(self.doc.customer)) or \
				(not acc_head and (self.doc.debit_to != cstr(self.doc.customer) + " - " + self.get_company_abbr())):
				msgprint("Debit To: %s do not match with Customer: %s for Company: %s.\n If both correctly entered, please select Master Type \
					and Master Name in account master." %(self.doc.debit_to, self.doc.customer,self.doc.company), raise_exception=1)


	# Validate Debit To Account
	# 1. Account Exists
	# 2. Is a Debit Account
	# 3. Is a PL Account
	# ---------------------------
	def validate_debit_acc(self):
		acc = webnotes.conn.sql("select debit_or_credit, is_pl_account from tabAccount where name = '%s' and docstatus != 2" % self.doc.debit_to)
		if not acc:
			msgprint("Account: "+ self.doc.debit_to + " does not exist")
			raise Exception
		elif acc[0][0] and acc[0][0] != 'Debit':
			msgprint("Account: "+ self.doc.debit_to + " is not a debit account")
			raise Exception
		elif acc[0][1] and acc[0][1] != 'No':
			msgprint("Account: "+ self.doc.debit_to + " is a pl account")
			raise Exception


	# Validate Fixed Asset Account and whether Income Account Entered Exists
	# -----------------------------------------------------------------------
	def validate_fixed_asset_account(self):
		for d in getlist(self.doclist,'entries'):
			item = webnotes.conn.sql("select name,is_asset_item,is_sales_item from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >	now())"% d.item_code)
			acc =	webnotes.conn.sql("select account_type from `tabAccount` where name = '%s' and docstatus != 2" % d.income_account)
			if not acc:
				msgprint("Account: "+d.income_account+" does not exist in the system")
				raise Exception
			elif item and item[0][1] == 'Yes' and not acc[0][0] == 'Fixed Asset Account':
				msgprint("Please select income head with account type 'Fixed Asset Account' as Item %s is an asset item" % d.item_code)
				raise Exception



	# Set totals in words
	#--------------------
	def set_in_words(self):
		dcc = TransactionBase().get_company_currency(self.doc.company)
		self.doc.in_words = get_obj('Sales Common').get_total_in_words(dcc, self.doc.rounded_total)
		self.doc.in_words_export = get_obj('Sales Common').get_total_in_words(self.doc.currency, self.doc.rounded_total_export)

	# Clear Advances
	# --------------
	def clear_advances(self):
		get_obj('GL Control').clear_advances(self, 'Sales Invoice Advance','advance_adjustment_details')


	# set aging date
	#-------------------
	def set_aging_date(self):
		if self.doc.is_opening != 'Yes':
			self.doc.aging_date = self.doc.posting_date
		elif not self.doc.aging_date:
			msgprint("Aging Date is mandatory for opening entry")
			raise Exception
			

	# Set against account for debit to account
	#------------------------------------------
	def set_against_income_account(self):
		against_acc = []
		for d in getlist(self.doclist, 'entries'):
			if d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.doc.against_income_account = ','.join(against_acc)

	def add_remarks(self):
		if not self.doc.remarks: self.doc.remarks = 'No Remarks'

	#check in manage account if sales order / delivery note required or not.
	def so_dn_required(self):
		dic = {'Sales Order':'so_required','Delivery Note':'dn_required'}
		for i in dic:	
			if webnotes.conn.get_value('Global Defaults', 'Global Defaults', dic[i]) == 'Yes':
				for d in getlist(self.doclist,'entries'):
					if webnotes.conn.get_value('Item', d.item_code, 'is_stock_item') == 'Yes' \
						and not d.fields[i.lower().replace(' ','_')]:
						msgprint("%s is mandatory for stock item which is not mentioed against item: %s"%(i,d.item_code), raise_exception=1)

	#check for does customer belong to same project as entered..
	#-------------------------------------------------------------------------------------------------
	def validate_proj_cust(self):
		if self.doc.project_name and self.doc.customer:
			res = webnotes.conn.sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in that project."%(self.doc.customer,self.doc.project_name))
				raise Exception

	def validate_pos(self):
		if not self.doc.cash_bank_account and flt(self.doc.paid_amount):
			msgprint("Cash/Bank Account is mandatory for POS, for making payment entry")
			raise Exception
		if (flt(self.doc.paid_amount) + flt(self.doc.write_off_amount) - round(flt(self.doc.grand_total), 2))>0.001:
			msgprint("(Paid amount + Write Off Amount) can not be greater than Grand Total")
			raise Exception


	# ********* UPDATE CURRENT STOCK *****************************
	def update_current_stock(self):
		for d in getlist(self.doclist, 'entries'):
			bin = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

	def validate_item_code(self):
		for d in getlist(self.doclist, 'entries'):
			if not d.item_code:
				msgprint("Please enter Item Code at line no : %s to update stock for POS or remove check from Update Stock in Basic Info Tab." % (d.idx))
				raise Exception

	# Validate Write Off Account
	# -------------------------------
	def validate_write_off_account(self):
		if flt(self.doc.write_off_amount) and not self.doc.write_off_account:
			msgprint("Please enter Write Off Account", raise_exception=1)


	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.doc.amended_from and self.doc.c_form_applicable == 'No' and self.doc.c_form_no:
			webnotes.conn.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.doc.amended_from,	self.doc.c_form_no))

			webnotes.conn.set(self.doc, 'c_form_no', '')
	 
	# VALIDATE
	# ====================================================================================
	def validate(self):
		self.so_dn_required()
		#self.dn_required()
		self.validate_proj_cust()
		sales_com_obj = get_obj('Sales Common')
		sales_com_obj.check_stop_sales_order(self)
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.check_conversion_rate(self)
		sales_com_obj.validate_max_discount(self, 'entries')	 #verify whether rate is not greater than tolerance
		sales_com_obj.get_allocated_sum(self)	# this is to verify that the allocated % of sales persons is 100%
		sales_com_obj.validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')
		self.validate_customer()
		self.validate_debit_to_acc()
		self.validate_debit_acc()
		self.validate_fixed_asset_account()
		self.add_remarks()
		if cint(self.doc.is_pos):
			self.validate_pos()
			self.validate_write_off_account()
			if cint(self.doc.update_stock):
				get_obj('Stock Ledger').validate_serial_no(self, 'entries')
				self.validate_item_code()
				self.update_current_stock()
		self.set_in_words()
		if not self.doc.is_opening:
			self.doc.is_opening = 'No'
		self.set_aging_date()
		self.clear_advances()
		# Set against account
		self.set_against_income_account()
		self.validate_c_form()

		
# *************************************************** ON SUBMIT **********************************************
	# Check Ref Document's docstatus
	# -------------------------------
	def check_prev_docstatus(self):
		for d in getlist(self.doclist,'entries'):
			if d.sales_order:
				submitted = webnotes.conn.sql("select name from `tabSales Order` where docstatus = 1 and name = '%s'" % d.sales_order)
				if not submitted:
					msgprint("Sales Order : "+ cstr(d.sales_order) +" is not submitted")
					raise Exception , "Validation Error."

			if d.delivery_note:
				submitted = webnotes.conn.sql("select name from `tabDelivery Note` where docstatus = 1 and name = '%s'" % d.delivery_note)
				if not submitted:
					msgprint("Delivery Note : "+ cstr(d.delivery_note) +" is not submitted")
					raise Exception , "Validation Error."


	#Set Actual Qty based on item code and warehouse
	#------------------------------------------------------
	def set_actual_qty(self):
		for d in getlist(self.doclist, 'entries'):
			if d.item_code and d.warehouse:
				actual_qty = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0



	# ********************** Make Stock Entry ************************************
	def make_sl_entry(self, d, wh, qty, in_value, update_stock):
		st_uom = webnotes.conn.sql("select stock_uom from `tabItem` where name = '%s'"%d.item_code)
		self.values.append({
			'item_code'					 : d.item_code,
			'warehouse'					 : wh,
			'transaction_date'			: getdate(self.doc.modified).strftime('%Y-%m-%d'),
			'posting_date'				: self.doc.posting_date,
			'posting_time'				: self.doc.posting_time,
			'voucher_type'				: 'Sales Invoice',
			'voucher_no'					: cstr(self.doc.name),
			'voucher_detail_no'	 : cstr(d.name), 
			'actual_qty'					: qty, 
			'stock_uom'					 : st_uom and st_uom[0][0] or '',
			'incoming_rate'			 : in_value,
			'company'						 : self.doc.company,
			'fiscal_year'				 : self.doc.fiscal_year,
			'is_cancelled'				: (update_stock==1) and 'No' or 'Yes',
			'batch_no'						: cstr(d.batch_no),
			'serial_no'					 : d.serial_no
		})		
			

	# UPDATE STOCK LEDGER
	# ---------------------------------------------------------------------------
	def update_stock_ledger(self, update_stock, clear = 0):
		self.values = []
		for d in getlist(self.doclist, 'entries'):
			stock_item = webnotes.conn.sql("SELECT is_stock_item, is_sample_item FROM tabItem where name = '%s'"%(d.item_code), as_dict = 1) # stock ledger will be updated only if it is a stock item
			if stock_item[0]['is_stock_item'] == "Yes":
				# Reduce actual qty from warehouse
				self.make_sl_entry( d, d.warehouse, - flt(d.qty) , 0, update_stock)
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values, self.doc.amended_from and 'Yes' or 'No')


	#-------------------POS Stock Updatation Part----------------------------------------------
	def pos_update_stock(self):
		self.update_stock_ledger(update_stock = 1)
	
	# ********** Get Actual Qty of item in warehouse selected *************
	def get_actual_qty(self,args):
		args = eval(args)
		actual_qty = webnotes.conn.sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], args['warehouse']), as_dict=1)
		ret = {
			 'actual_qty' : actual_qty and flt(actual_qty[0]['actual_qty']) or 0
		}
		return ret

	# Make GL Entries
	# -------------------------
	def make_gl_entries(self, is_cancel=0):
		mapper = self.doc.is_pos and self.doc.write_off_account and 'POS with write off' or self.doc.is_pos and not self.doc.write_off_account and 'POS' or ''
		update_outstanding = self.doc.is_pos and self.doc.write_off_account and 'No' or 'Yes'
		get_obj(dt='GL Control').make_gl_entries(self.doc, self.doclist,cancel = is_cancel, use_mapper = mapper, update_outstanding = update_outstanding, merge_entries = cint(self.doc.is_pos) != 1 and 1 or 0)
		

	# On Submit
	# ---------
	def on_submit(self):
		if cint(self.doc.is_pos) == 1:
			if cint(self.doc.update_stock) == 1:
				sl_obj = get_obj("Stock Ledger")
				sl_obj.validate_serial_no_warehouse(self, 'entries')
				sl_obj.update_serial_record(self, 'entries', is_submit = 1, is_incoming = 0)
				self.pos_update_stock()
		else:
			self.check_prev_docstatus()
			get_obj("Sales Common").update_prevdoc_detail(1,self)

			# Check for Approving Authority
			if not self.doc.recurring_id:
				get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)

		# this sequence because outstanding may get -ve		
		self.make_gl_entries()

		if not cint(self.doc.is_pos) == 1:
			self.update_against_document_in_jv()

		self.update_c_form()


	def update_c_form(self):
		"""Update amended id in C-form"""
		if self.doc.c_form_no and self.doc.amended_from:
			webnotes.conn.sql("""update `tabC-Form Invoice Detail` set invoice_no = %s,
					invoice_date = %s, territory = %s, net_total = %s,
					grand_total = %s where invoice_no = %s and parent = %s""", (self.doc.name, self.doc.amended_from, self.doc.c_form_no))
	

			
# *************************************************** ON CANCEL **********************************************
	# Check Next Document's docstatus
	# --------------------------------
	def check_next_docstatus(self):
		submit_jv = webnotes.conn.sql("select t1.name from `tabJournal Voucher` t1,`tabJournal Voucher Detail` t2 where t1.name = t2.parent and t2.against_invoice = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_jv:
			msgprint("Journal Voucher : " + cstr(submit_jv[0][0]) + " has been created against " + cstr(self.doc.doctype) + ". So " + cstr(self.doc.doctype) + " cannot be Cancelled.")
			raise Exception, "Validation Error."


	# On Cancel
	# ----------
	def on_cancel(self):
		if cint(self.doc.is_pos) == 1:
			if cint(self.doc.update_stock) == 1:
				get_obj('Stock Ledger').update_serial_record(self, 'entries', is_submit = 0, is_incoming = 0)
				self.update_stock_ledger(update_stock = -1)
		else:
			sales_com_obj = get_obj(dt = 'Sales Common')
			sales_com_obj.check_stop_sales_order(self)
			self.check_next_docstatus()
			sales_com_obj.update_prevdoc_detail(0,self)

		self.make_gl_entries(is_cancel=1)

	# Get Warehouse
	def get_warehouse(self):
		w = webnotes.conn.sql("select warehouse from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company))
		w = w and w[0][0] or ''
		if not w:
			ps = webnotes.conn.sql("select name, warehouse from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % self.doc.company)
			if not ps:
				msgprint("To make POS entry, please create POS Setting from Setup --> Accounts --> POS Setting and refresh the system.")
				raise Exception
			elif not ps[0][1]:
				msgprint("Please enter warehouse in POS Setting")
			else:
				w = ps[0][1]
		return w

	# on update
	def on_update(self):
		# Set default warehouse from pos setting
		#----------------------------------------
		if cint(self.doc.is_pos) == 1:
			self.set_actual_qty()
			w = self.get_warehouse()
			if w:
				for d in getlist(self.doclist, 'entries'):
					if not d.warehouse:
						d.warehouse = cstr(w)

			if flt(self.doc.paid_amount) == 0:
				if self.doc.cash_bank_account: 
					webnotes.conn.set(self.doc, 'paid_amount', 
						(flt(self.doc.grand_total) - flt(self.doc.write_off_amount)))
				else:
					# show message that the amount is not paid
					webnotes.conn.set(self.doc,'paid_amount',0)
					webnotes.msgprint("Note: Payment Entry not created since 'Cash/Bank Account' was not specified.")

		else:
			webnotes.conn.set(self.doc,'paid_amount',0)

		webnotes.conn.set(self.doc,'outstanding_amount',flt(self.doc.grand_total) - flt(self.doc.total_advance) - flt(self.doc.paid_amount) - flt(self.doc.write_off_amount))

	#-------------------------------------------------------------------------------------

	def set_default_recurring_values(self):
		from webnotes.utils import cstr

		owner_email = self.doc.owner
		if owner_email.lower() == 'administrator':
			owner_email = cstr(webnotes.conn.get_value("Profile", "Administrator", "email"))
		
		ret = {
			'repeat_on_day_of_month' : getdate(self.doc.posting_date).day,
			'notification_email_address' : ', '.join([owner_email, cstr(self.doc.contact_email)]),
		}
		return ret
		
	def validate_notification_email_id(self):
		if self.doc.notification_email_address:
			from webnotes.utils import validate_email_add
			for add in self.doc.notification_email_address.replace('\n', '').replace(' ', '').split(","):
				if add and not validate_email_add(add):
					msgprint("%s is not a valid email address" % add, raise_exception=1)
		else:
			msgprint("Notification Email Addresses not specified for recurring invoice",
				raise_exception=1)
		
		
	def on_update_after_submit(self):
		self.convert_into_recurring()
		
		
	def convert_into_recurring(self):
		if self.doc.convert_into_recurring_invoice:
			self.validate_notification_email_id()
			
			if not self.doc.recurring_type:
				msgprint("Please select recurring type", raise_exception=1)
			elif not self.doc.invoice_period_from_date or not self.doc.invoice_period_to_date:
				msgprint("Invoice period from date and to date is mandatory for recurring invoice", raise_exception=1)
			self.set_next_date()
			if not self.doc.recurring_id:
				webnotes.conn.set(self.doc, 'recurring_id', make_autoname('RECINV/.#####'))
		elif self.doc.recurring_id:
			webnotes.conn.sql("""update `tabSales Invoice` set convert_into_recurring_invoice = 0 where recurring_id = %s""", self.doc.recurring_id)

	def set_next_date(self):
		""" Set next date on which auto invoice will be created"""

		if not self.doc.repeat_on_day_of_month:
			msgprint("""Please enter 'Repeat on Day of Month' field value. \nThe day of the month on which auto invoice 
						will be generated e.g. 05, 28 etc.""", raise_exception=1)

		import datetime
		mcount = {'Monthly': 1, 'Quarterly': 3, 'Half-yearly': 6, 'Yearly': 12}
		m = getdate(self.doc.posting_date).month + mcount[self.doc.recurring_type]
		y = getdate(self.doc.posting_date).year
		if m > 12:
			m, y = m-12, y+1
		try:
			next_date = datetime.date(y, m, cint(self.doc.repeat_on_day_of_month))
		except:
			import calendar
			last_day = calendar.monthrange(y, m)[1]
			next_date = datetime.date(y, m, last_day)
		next_date = next_date.strftime("%Y-%m-%d")

		webnotes.conn.set(self.doc, 'next_date', next_date)
