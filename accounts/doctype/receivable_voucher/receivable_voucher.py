# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
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
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.log = []
		self.tname = 'RV Detail'
		self.fname = 'entries'


	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')



# ********************************* Trigger Functions ******************************

	#Set retail related fields from pos settings
	#-------------------------------------------------------------------------
	def set_pos_fields(self):
		pos = sql("select * from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)
		if not pos:
			pos = sql("select * from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)
		if pos:
			val = sql("select name from `tabAccount` where name = %s and docstatus != 2", (cstr(self.doc.customer) + " - " + self.get_company_abbr()))
			val = val and val[0][0] or ''
			if not val: val = pos and pos[0]['customer_account'] or ''
			if not self.doc.debit_to:
				set(self.doc,'debit_to',val)
			
			lst = ['territory','naming_series','currency','charge','letter_head','tc_name','price_list_name','company','select_print_heading','cash_bank_account']
				
			for i in lst:
				val = pos and pos[0][i] or ''
				set(self.doc,i,val)
			self.set_pos_item_values()
			
			val = pos and flt(pos[0]['conversion_rate']) or 0	
			set(self.doc,'conversion_rate',val)

			#fetch terms	
			if self.doc.tc_name:	 self.get_tc_details()
			
			#fetch charges
			if self.doc.charge:		self.get_other_charges()


	# Set default values related to pos for previously created sales invoice.
	# -------------------------------------------------------------------------- 
	def set_pos_item_values(self):
		if cint(self.doc.is_pos) ==1:
			dtl = sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)
			if not dtl:
				dtl = sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)
			for d in getlist(self.doclist,'entries'):
				if dtl and dtl[0]['income_account']: d.income_account = dtl[0]['income_account']
				if dtl and dtl[0]['cost_center']: d.cost_center = dtl[0]['cost_center']
				if dtl and dtl[0]['warehouse']: d.warehouse = dtl[0]['warehouse']

			
	# Get Account Head to which amount needs to be Debited based on Customer
	# ----------------------------------------------------------------------
	def get_customer_account(self):
		acc_head = sql("select name from `tabAccount` where (name = %s or (master_name = %s and master_type = 'customer')) and docstatus != 2", (cstr(self.doc.customer) + " - " + self.get_company_abbr(),self.doc.customer))
		if acc_head and acc_head[0][0]:
			return acc_head[0][0]
		else:
			msgprint("%s does not have an Account Head in %s. You must first create it from the Customer Master" % (self.doc.customer, self.doc.company))

	def get_debit_to(self):
		acc_head = self.get_customer_account()
		if acc_head:
			return { 'debit_to' : acc_head }


	# Set Due Date = Posting Date + Credit Days
	# -----------------------------------------
	def get_cust_and_due_date(self):
		credit_days = 0
		if self.doc.debit_to:
			credit_days = sql("select credit_days from `tabAccount` where name='%s' and docstatus != 2" % self.doc.debit_to)
			credit_days = credit_days and cint(credit_days[0][0]) or 0
		if self.doc.company and not credit_days:
			credit_days = sql("select credit_days from `tabCompany` where name='%s'" % self.doc.company)
			credit_days = credit_days and cint(credit_days[0][0]) or 0
		# Customer has higher priority than company
		# i.e.if not entered in customer will take credit days from company
		self.doc.due_date = add_days(cstr(self.doc.posting_date), credit_days)
		
		if self.doc.debit_to:
			self.doc.customer = get_value('Account',self.doc.debit_to,'master_name')
		#	get_obj('Sales Common').get_customer_details(self, inv_det_reqd = 0)


	# Pull Details of Delivery Note or Sales Order Selected
	# ------------------------------------------------------
	def pull_details(self):
		# Delivery Note
		if self.doc.delivery_note_main:
			self.validate_prev_docname('delivery note')
			self.doc.clear_table(self.doclist,'other_charges')			
			self.doclist = get_obj('DocType Mapper', 'Delivery Note-Receivable Voucher').dt_map('Delivery Note', 'Receivable Voucher', self.doc.delivery_note_main, self.doc, self.doclist, "[['Delivery Note', 'Receivable Voucher'],['Delivery Note Detail', 'RV Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]")			
			self.get_income_account('entries')
		# Sales Order
		elif self.doc.sales_order_main:
			self.validate_prev_docname('sales order')
			self.doc.clear_table(self.doclist,'other_charges')
			get_obj('DocType Mapper', 'Sales Order-Receivable Voucher').dt_map('Sales Order', 'Receivable Voucher', self.doc.sales_order_main, self.doc, self.doclist, "[['Sales Order', 'Receivable Voucher'],['Sales Order Detail', 'RV Detail'],['RV Tax Detail','RV Tax Detail'], ['Sales Team', 'Sales Team']]")
			self.get_income_account('entries')
			
		ret = eval(self.get_debit_to())	
		if ret.has_key('debit_to'):
			self.doc.debit_to = ret['debit_to']
					
	# onload pull income account
	# --------------------------
	def load_default_accounts(self):
		"""
			Loads default accounts from items, customer when called from mapper
		"""
		self.get_income_account('entries')
		self.doc.debit_to = self.get_customer_account()
		
	def get_income_account(self,doctype):		
		for d in getlist(self.doclist, doctype):			
			if d.item_code:
				item = sql("select default_income_account, default_sales_cost_center from tabItem where name = '%s'" %(d.item_code), as_dict=1)
				d.income_account = item and item[0]['default_income_account'] or ''
				d.cost_center = item and item[0]['default_sales_cost_center'] or ''				

	# Item Details
	# -------------
	def get_item_details(self, item_code):
		ret = get_obj('Sales Common').get_item_details(item_code, self)
		if item_code and cint(self.doc.is_pos) == 1:
			dtl = sql("select income_account, warehouse, cost_center from `tabPOS Setting` where user = '%s' and company = '%s'" % (session['user'], self.doc.company), as_dict=1)				 
			if not dtl:
				dtl = sql("select income_account, warehouse, cost_center from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % (self.doc.company), as_dict=1)
			if dtl and dtl[0]['income_account']: ret['income_account'] = dtl and dtl[0]['income_account']
			if dtl and dtl[0]['cost_center']: ret['cost_center'] = dtl and dtl[0]['cost_center']
			if dtl and dtl[0]['warehouse']: ret['warehouse'] = dtl and dtl[0]['warehouse']
			if ret['warehouse']:
				actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (item_code, ret['warehouse']))		
				ret['actual_qty']= actual_qty and flt(actual_qty[0][0]) or 0
		return ret
 

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
		return get_obj('Sales Common').load_default_taxes(self)

	# Get Other Charges Details
	# --------------------------
	def get_other_charges(self):
		return get_obj('Sales Common').get_other_charges(self)
		

	# Get Advances
	# -------------
	def get_advances(self):
		get_obj('GL Control').get_advances(self, self.doc.debit_to, 'Advance Adjustment Detail', 'advance_adjustment_details', 'credit')

	#pull project customer
	#-------------------------
	def pull_project_customer(self):
		res = sql("select customer from `tabProject` where name = '%s'"%self.doc.project_name)
		if res:
			get_obj('DocType Mapper', 'Project-Receivable Voucher').dt_map('Project', 'Receivable Voucher', self.doc.project_name, self.doc, self.doclist, "[['Project', 'Receivable Voucher']]")

# ********************************** Server Utility Functions ******************************
	
	# Get Company Abbr.
	# ------------------
	def get_company_abbr(self):
		return sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
		
	
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
	# ADVANCE ALLOCATION
	#-----------------------------------------------------------------
	def update_against_document_in_jv(self,against_document_no, against_document_doctype):
		get_obj('GL Control').update_against_document_in_jv( self, 'advance_adjustment_details', against_document_no, against_document_doctype, self.doc.debit_to, 'credit', self.doc.doctype)
	


# ************************************* VALIDATE **********************************************
	# Get Customer Name and address based on Debit To Account selected
	# This case arises in case of direct RV where user doesn't enter customer name.
	# Hence it should be fetched from Account Head.
	# -----------------------------------------------------------------------------
	#def get_customer_details(self):
	#	get_obj('Sales Common').get_customer_details(self, inv_det_reqd = 1)
	#	self.get_cust_and_due_date()

	
	# Validate Customer Name with SO or DN if items are fetched from SO or DN
	# ------------------------------------------------------------------------
	def validate_customer(self):
		for d in getlist(self.doclist,'entries'):
			customer = ''
			if d.sales_order:
				customer = sql("select customer from `tabSales Order` where name = '%s'" % d.sales_order)[0][0]
				doctype = 'sales order'
				doctype_no = cstr(d.sales_order)
			if d.delivery_note:
				customer = sql("select customer from `tabDelivery Note` where name = '%s'" % d.delivery_note)[0][0]
				doctype = 'delivery note'
				doctype_no = cstr(d.delivery_note)
			if customer and not cstr(self.doc.customer) == cstr(customer):
				msgprint("Customer %s do not match with customer	of %s %s." %(self.doc.customer,doctype,doctype_no))
				raise Exception , " Validation Error "
		

	# Validates Debit To Account and Customer Matches
	# ------------------------------------------------
	def validate_debit_to_acc(self):
		if self.doc.customer and not cint(self.doc.is_pos):
			acc_head = sql("select name from `tabAccount` where name = %s and docstatus != 2", (cstr(self.doc.customer) + " - " + self.get_company_abbr()))
			if acc_head and acc_head[0][0]:
				if not cstr(acc_head[0][0]) == cstr(self.doc.debit_to):
					msgprint("Debit To %s do not match with Customer %s for Company %s i.e. %s" %(self.doc.debit_to,self.doc.customer,self.doc.company,cstr(acc_head[0][0])))
					raise Exception, "Validation Error "
			if not acc_head:
				 msgprint("%s does not have an Account Head in %s. You must first create it from the Customer Master" % (self.doc.customer, self.doc.company))
				 raise Exception, "Validation Error "


	# Validate Debit To Account
	# 1. Account Exists
	# 2. Is a Debit Account
	# 3. Is a PL Account
	# ---------------------------
	def validate_debit_acc(self):
		acc = sql("select debit_or_credit, is_pl_account from tabAccount where name = '%s' and docstatus != 2" % self.doc.debit_to)
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
			item = sql("select name,is_asset_item,is_sales_item from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >	now())"% d.item_code)
			acc =	sql("select account_type from `tabAccount` where name = '%s' and docstatus != 2" % d.income_account)
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
		get_obj('GL Control').clear_advances(self, 'Advance Adjustment Detail','advance_adjustment_details')


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
		dict = {'Sales Order':'so_required','Delivery Note':'dn_required'}
		for i in dict:	
			res = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = '%s'"%dict[i])
			if res and res[0][0] == 'Yes':
				for d in getlist(self.doclist,'entries'):
					if not d.fields[i.lower().replace(' ','_')]:
						msgprint("%s No. required against item %s"%(i,d.item_code))
						raise Exception

	#check for does customer belong to same project as entered..
	#-------------------------------------------------------------------------------------------------
	def validate_proj_cust(self):
		if self.doc.project_name and self.doc.customer:
			res = sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in that project."%(self.doc.customer,self.doc.project_name))
				raise Exception

	def validate_pos(self):
		if not self.doc.cash_bank_account:
			msgprint("Cash/Bank Account is mandatory for POS entry")
			raise Exception
		if (flt(self.doc.paid_amount) + flt(self.doc.write_off_amount) - flt(self.doc.grand_total))>0.001:
			msgprint("(Paid amount + Write Off Amount) can not be greater than Grand Total")
			raise Exception


	# ********* UPDATE CURRENT STOCK *****************************
	def update_current_stock(self):
		for d in getlist(self.doclist, 'entries'):
			bin = sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
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
		if not self.doc.customer:
			get_obj('Sales Common').get_customer_details(self, inv_det_reqd = 0)
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

		
# *************************************************** ON SUBMIT **********************************************
	# Check Ref Document's docstatus
	# -------------------------------
	def check_prev_docstatus(self):
		for d in getlist(self.doclist,'entries'):
			if d.sales_order:
				submitted = sql("select name from `tabSales Order` where docstatus = 1 and name = '%s'" % d.sales_order)
				if not submitted:
					msgprint("Sales Order : "+ cstr(d.sales_order) +" is not submitted")
					raise Exception , "Validation Error."

			if d.delivery_note:
				submitted = sql("select name from `tabDelivery Note` where docstatus = 1 and name = '%s'" % d.delivery_note)
				if not submitted:
					msgprint("Delivery Note : "+ cstr(d.delivery_note) +" is not submitted")
					raise Exception , "Validation Error."

	#Set Actual Qty based on item code and warehouse
	#------------------------------------------------------
	def set_actual_qty(self):
		for d in getlist(self.doclist, 'delivery_note_details'):
			if d.item_code and d.warehouse:
				actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0					

	# Check qty in stock depends on item code and warehouse
	#-------------------------------------------------------
	def check_qty_in_stock(self):
		for d in getlist(self.doclist, 'entries'):
			is_stock_item = sql("select is_stock_item from `tabItem` where name = '%s'" % d.item_code)[0][0]
			actual_qty = 0
			if d.item_code and d.warehouse:
				actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code, d.warehouse))
				actual_qty = actual_qty and flt(actual_qty[0][0]) or 0

			if is_stock_item == 'Yes' and flt(d.qty) > flt(actual_qty):
				msgprint("For Item: " + cstr(d.item_code) + " at Warehouse: " + cstr(d.warehouse) + " Quantity: " + cstr(d.qty) +" is not Available. (Must be less than or equal to " + cstr(actual_qty) + " )")
				raise Exception, "Validation Error"

	

	# ********************** Make Stock Entry ************************************
	def make_sl_entry(self, d, wh, qty, in_value, update_stock):
		st_uom = sql("select stock_uom from `tabItem` where name = '%s'"%d.item_code)
		self.values.append({
			'item_code'					 : d.item_code,
			'warehouse'					 : wh,
			'transaction_date'		: self.doc.voucher_date,
			'posting_date'				: self.doc.posting_date,
			'posting_time'				: self.doc.posting_time,
			'voucher_type'				: 'Receivable Voucher',
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
			stock_item = sql("SELECT is_stock_item, is_sample_item FROM tabItem where name = '%s'"%(d.item_code), as_dict = 1) # stock ledger will be updated only if it is a stock item
			if stock_item[0]['is_stock_item'] == "Yes":
				# Reduce actual qty from warehouse
				self.make_sl_entry( d, d.warehouse, - flt(d.qty) , 0, update_stock)
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values)


	#-------------------POS Stock Updatation Part----------------------------------------------
	def pos_update_stock(self):
		self.check_qty_in_stock()	
		self.update_stock_ledger(update_stock = 1)
	
	# ********** Get Actual Qty of item in warehouse selected *************
	def get_actual_qty(self,args):
		args = eval(args)
		actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], args['warehouse']), as_dict=1)
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
			get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)

		# this sequence because outstanding may get -ve		
		self.make_gl_entries()

		if not cint(self.doc.is_pos) == 1:
			self.update_against_document_in_jv(self.doc.name, self.doc.doctype)
		
		# on submit notification
		# get_obj('Notification Control').notify_contact('Sales Invoice', self.doc.doctype,self.doc.name, self.doc.email_id, self.doc.contact_person)
		
			
# *************************************************** ON CANCEL **********************************************
	# Check Next Document's docstatus
	# --------------------------------
	def check_next_docstatus(self):
		submit_jv = sql("select t1.name from `tabJournal Voucher` t1,`tabJournal Voucher Detail` t2 where t1.name = t2.parent and t2.against_invoice = '%s' and t1.docstatus = 1" % (self.doc.name))
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
		w = sql("select warehouse from `tabPOS Setting` where ifnull(user,'') = '%s' and company = '%s'" % (session['user'], self.doc.company))
		if not w:
			ps = sql("select name, warehouse from `tabPOS Setting` where ifnull(user,'') = '' and company = '%s'" % self.doc.company)
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
				set(self.doc,'paid_amount',(flt(self.doc.grand_total) - flt(self.doc.write_off_amount)))

		else:
			set(self.doc,'paid_amount',0)

		set(self.doc,'outstanding_amount',flt(self.doc.grand_total) - flt(self.doc.total_advance) - flt(self.doc.paid_amount) - flt(self.doc.write_off_amount))


########################################################################
# Repair Outstanding
#######################################################################
	def repair_rv_outstanding(self):
		get_obj(dt = 'GL Control').repair_voucher_outstanding(self)
