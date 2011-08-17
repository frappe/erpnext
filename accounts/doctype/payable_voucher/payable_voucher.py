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
		self.tname = 'PV Detail'
		self.fname = 'entries'

	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.####')


# ************************** Trigger Functions ****************************

	# Credit To
	# ----------
	def get_credit_to(self):
		acc_head = sql("select name, credit_days from `tabAccount` where (name = %s or (master_name = %s and master_type = 'supplier')) and docstatus != 2", (cstr(self.doc.supplier) + " - " + self.get_company_abbr(),self.doc.supplier))		
		#supp_detail = sql("select supplier_name,address from `tabSupplier` where name = %s", self.doc.supplier, as_dict =1)
		#ret = {
		#	'supplier_name' : supp_detail and supp_detail[0]['supplier_name'] or '',
		#	'supplier_address': supp_detail and supp_detail[0]['address'] or ''
		#}
		ret = {}
		if acc_head and acc_head[0][0]:
			ret['credit_to'] = acc_head[0][0]
			if not self.doc.due_date:
				ret['due_date'] = add_days(cstr(self.doc.posting_date), acc_head and cint(acc_head[0][1]) or 0)
		elif not acc_head:
			msgprint("%s does not have an Account Head in %s. You must first create it from the Supplier Master" % (self.doc.supplier, self.doc.company))
		return ret
		
	def get_cust(self):
		ret = {}
		if self.doc.credit_to:			
			ret['supplier'] = get_value('Account',self.doc.credit_to,'master_name')
			
		return ret


	# Get Default Cost Center and Expense Head from Item Master
	# ----------------------------------------------------------
	def get_default_values(self,args):
		args = eval(args)
		ret = {}
		if sql("select name from `tabItem` where name = '%s'" % args['item_code']):
			if not args['expense_head'] or args['expense_head'] == 'undefined':
				expense_head = sql("select name from `tabAccount` where account_name in (select purchase_account from `tabItem` where name = '%s')" % args['item_code'])
				ret['expense_head'] = expense_head and expense_head[0][0] or ''
			if not args['cost_center'] or args['cost_center'] == 'undefined':
				cost_center = sql("select cost_center from `tabItem` where name = '%s'" % args['item_code'])
				ret['cost_center'] = cost_center and cost_center[0][0] or ''
		return ret
		 
	
	# Get Items based on PO or PR
	# ----------------------------
	def pull_details(self):
		if self.doc.purchase_receipt_main:
			self.validate_duplicate_docname('purchase_receipt')
			self.doclist = get_obj('DocType Mapper', 'Purchase Receipt-Payable Voucher').dt_map('Purchase Receipt', 'Payable Voucher', self.doc.purchase_receipt_main, self.doc, self.doclist, "[['Purchase Receipt', 'Payable Voucher'],['Purchase Receipt Detail', 'PV Detail']]")

		elif self.doc.purchase_order_main:
			self.validate_duplicate_docname('purchase_order')
			self.doclist = get_obj('DocType Mapper', 'Purchase Order-Payable Voucher').dt_map('Purchase Order', 'Payable Voucher', self.doc.purchase_order_main, self.doc, self.doclist, "[['Purchase Order', 'Payable Voucher'],['PO Detail', 'PV Detail']]")
		
		ret = eval(self.get_credit_to())
		#self.doc.supplier_name = ret['supplier_name']
		#self.doc.supplier_address = ret['supplier_address']
		
		#self.doc.cst_no =ret['cst_no']
		#self.doc.bst_no = ret['bst_no']
		#self.doc.vat_tin_no = ret['vat_tin_no']

		if ret.has_key('credit_to'):
			self.doc.credit_to = ret['credit_to']
			

	# Get Item Details
	# -----------------		
	def get_item_details(self,arg):
		item_det = sql("select item_name, brand, description, item_group,purchase_account,cost_center from tabItem where name=%s",arg,as_dict=1)
		tax = sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , arg)
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'item_name' : item_det and item_det[0]['item_name'] or '',
			'brand' : item_det and item_det[0]['brand'] or '',
			'description' : item_det and item_det[0]['description'] or '',
			'item_group'	: item_det and item_det[0]['item_group'] or '',
			'rate' : 0.00,
			'qty' : 0.00,
			'amount' : 0.00,
			'expense_head' : item_det and item_det[0]['purchase_account'] or '',
			'cost_center' : item_det and item_det[0]['cost_center'] or '',
			'item_tax_rate'			: str(t)
		}
		return ret
		
	# Advance Allocation
	# -------------------
	def get_advances(self):
		get_obj('GL Control').get_advances( self, self.doc.credit_to, 'Advance Allocation Detail','advance_allocation_details','debit')
		
		
	# ============= OTHER CHARGES ====================
	
	# Get Tax rate if account type is TAX
	# ------------------------------------
	def get_rate(self,arg):
		return get_obj('Purchase Common').get_rate(arg,self)

	# Pull details from other charges master (Get Other Charges)
	# -----------------------------------------------------------
	def get_purchase_tax_details(self):
		return get_obj('Purchase Common').get_purchase_tax_details(self)


	def get_rate1(self,acc):
		rate = sql("select tax_rate from `tabAccount` where name='%s'"%(acc))
		ret={'add_tax_rate' :rate and flt(rate[0][0]) or 0 }
		return ret
	

# *************************** Server Utility Functions *****************************
	# Get Company abbr
	# -----------------
	def get_company_abbr(self):
		return sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]

	# Check whether PO or PR is already fetched
	# ------------------------------------------
	def validate_duplicate_docname(self,doctype):
		for d in getlist(self.doclist, 'entries'): 
			if doctype == 'purchase_receipt' and cstr(self.doc.purchase_receipt_main) == cstr(d.purchase_receipt):
				msgprint(cstr(self.doc.purchase_receipt_main) + " purchase receipt details have already been pulled.")
				raise Exception , " Validation Error. "

			if doctype == 'purchase_order' and cstr(self.doc.purchase_order_main) == cstr(d.purchase_order) and not d.purchase_receipt:
				msgprint(cstr(self.doc.purchase_order_main) + " purchase order details have already been pulled.")
				raise Exception , " Validation Error. "

		
# **************************** VALIDATE ********************************

	# Check for Item.is_Purchase_item = 'Yes' and Item is active
	# ------------------------------------------------------------------
	def check_active_purchase_items(self):
		for d in getlist(self.doclist, 'entries'):
			if d.item_code:		# extra condn coz item_code is not mandatory in PV
				valid_item = sql("select docstatus,is_purchase_item from tabItem where name = %s",d.item_code)
				if valid_item[0][0] == 2:
					msgprint("Item : '%s' is Inactive, you can restore it from Trash" %(d.item_code))
					raise Exception
				if not valid_item[0][1] == 'Yes':
					msgprint("Item : '%s' is not Purchase Item"%(d.item_code))
					raise Exception
						
	# Check Conversion Rate
	# ----------------------
	def check_conversion_rate(self):
		default_currency = TransactionBase().get_company_currency(self.doc.company)		
		if not default_currency:
			msgprint('Message: Please enter default currency in Company Master')
			raise Exception
		if (self.doc.currency == default_currency and flt(self.doc.conversion_rate) != 1.00) or not self.doc.conversion_rate or (self.doc.currency != default_currency and flt(self.doc.conversion_rate) == 1.00):
			msgprint("Message: Please Enter Appropriate Conversion Rate.")
			raise Exception				

	# 1. Check whether bill is already booked against this bill no. or not
	# 2. Add Remarks
	# ---------------------------------------------------------------------
	def validate_bill_no(self):
		if self.doc.bill_no and self.doc.bill_no.lower().strip()	not in ['na', 'not applicable', 'none']:
			b_no = sql("select bill_no, name, ifnull(is_opening,'') from `tabPayable Voucher` where bill_no = '%s' and credit_to = '%s' and docstatus = 1 and name != '%s' " % (self.doc.bill_no, self.doc.credit_to, self.doc.name))
			if b_no and cstr(b_no[0][2]) == cstr(self.doc.is_opening):
				msgprint("Please check you have already booked expense against Bill No. %s in Purchase Invoice %s" % (cstr(b_no[0][0]), cstr(b_no[0][1])))
				raise Exception , "Validation Error"
			if not self.doc.remarks:
				self.doc.remarks = (self.doc.remarks or '') + "\n" + ("Against Bill %s dated %s" % (self.doc.bill_no, formatdate(self.doc.bill_date)))
				if self.doc.ded_amount:
					self.doc.remarks = (self.doc.remarks or '') + "\n" + ("Grand Total: %s, Tax Deduction Amount: %s" %(self.doc.grand_total, self.doc.ded_amount))
		else:
			if not self.doc.remarks:
				self.doc.remarks = "No Remarks"
					
	# Validate Bill No Date
	# ---------------------
	def validate_bill_no_date(self):
		if self.doc.bill_no and not self.doc.bill_date and self.doc.bill_no.lower().strip() not in ['na', 'not applicable', 'none']:
			msgprint("Please enter Bill Date")
			raise Exception					


 
	# Clear Advances
	# ---------------
	def clear_advances(self):
		get_obj('GL Control').clear_advances( self, 'Advance Allocation Detail','advance_allocation_details')


	# 1. Credit To Account Exists
	# 2. Is a Credit Account
	# 3. Is not a PL Account
	# ----------------------------
	def validate_credit_acc(self):
		acc = sql("select debit_or_credit, is_pl_account from tabAccount where name = '%s'" % self.doc.credit_to)
		if not acc:
			msgprint("Account: "+ self.doc.credit_to + "does not exist")
			raise Exception
		elif acc[0][0] and acc[0][0] != 'Credit':
			msgprint("Account: "+ self.doc.credit_to + "is not a credit account")
			raise Exception
		elif acc[0][1] and acc[0][1] != 'No':
			msgprint("Account: "+ self.doc.credit_to + "is a pl account")
			raise Exception
	
	# Validate Acc Head of Supplier and Credit To Account entered
	# ------------------------------------------------------------
	def check_for_acc_head_of_supplier(self): 
		acc_head = sql("select name from `tabAccount` where name = %s", (cstr(self.doc.supplier) + " - " + self.get_company_abbr()))
		if self.doc.supplier:
			if acc_head and acc_head[0][0]:
				if not cstr(acc_head[0][0]) == cstr(self.doc.credit_to):
					msgprint("Credit To: %s do not match with Supplier: %s for Company: %s i.e. %s" %(self.doc.credit_to,self.doc.supplier,self.doc.company,cstr(acc_head[0][0])))
					raise Exception, "Validation Error "
			if not acc_head:
				msgprint("Supplier %s does not have an Account Head in %s. You must first create it from the Supplier Master" % (self.doc.supplier, self.doc.company))
				raise Exception, "Validation Error "
				
	# Check for Stopped PO
	# ---------------------
	def check_for_stopped_status(self):
		check_list = []
		for d in getlist(self.doclist,'entries'):
			if d.purchase_order and not d.purchase_order in check_list and not d.purchase_receipt:
				check_list.append(d.purhcase_order)
				stopped = sql("select name from `tabPurchase Order` where status = 'Stopped' and name = '%s'" % d.purchase_order)
				if stopped:
					msgprint("One cannot do any transaction against 'Purchase Order' : %s, it's status is 'Stopped'" % (d.purhcase_order))
					raise Exception
					
	# Validate Supplier
	# -----------------
	def validate_supplier(self, d):
		supplier = ''
		if d.purchase_order and not d.purchase_order in self.po_list:
			supplier = sql("select supplier from `tabPurchase Order` where name = '%s'" % d.purchase_order)[0][0]
			doctype = 'purchase order'
			doctype_no = cstr(d.purchase_order)
			if supplier and not cstr(self.doc.supplier) == cstr(supplier):
				msgprint("Supplier name %s do not match with supplier name	of %s %s." %(self.doc.supplier,doctype,doctype_no))
				raise Exception , " Validation Error "

		if d.purchase_receipt and not d.purchase_receipt in self.pr_list:
			supplier = sql("select supplier from `tabPurchase Receipt` where name = '%s'" % d.purchase_receipt)[0][0]
			doctype = 'purchase receipt'
			doctype_no = cstr(d.purchase_receipt)
			if supplier and not cstr(self.doc.supplier) == cstr(supplier):
				msgprint("Supplier name %s do not match with supplier name	of %s %s." %(self.doc.supplier,doctype,doctype_no))
				raise Exception , " Validation Error "

	# Validate values with reference document
	#----------------------------------------
	def validate_reference_value(self):
		get_obj('DocType Mapper', 'Purchase Order-Payable Voucher', with_children = 1).validate_reference_value(self, self.doc.name)

				
	# Validate PO and PR
	# -------------------
	def validate_po_pr(self, d):
		# check po / pr for qty and rates and currency and conversion rate

		# always import_rate must be equal to import_rate of purchase order
		if d.purchase_order and not d.purchase_order in self.po_list:
			# currency
			currency = cstr(sql("select currency from `tabPurchase Order` where name = '%s'" % d.purchase_order)[0][0])
			if not cstr(currency) == cstr(self.doc.currency):
				msgprint("Purchase Order: " + cstr(d.purchase_order) + " currency : " + cstr(currency) + " does not match with currency of current document.")
				raise Exception
			# import_rate
			rate = flt(sql('select import_rate from `tabPO Detail` where item_code=%s and parent=%s and name = %s', (d.item_code, d.purchase_order, d.po_detail))[0][0])
			if abs(rate - flt(d.import_rate)) > 1:
				msgprint("Import Rate for %s in the Purchase Order is %s. Rate must be same as Purchase Order Rate" % (d.item_code,rate))
				raise Exception
									
		if d.purchase_receipt and not d.purchase_receipt in self.pr_list:
			# currency , conversion_rate
			data = sql("select currency, conversion_rate from `tabPurchase Receipt` where name = '%s'" % d.purchase_receipt, as_dict = 1)
			if not cstr(data[0]['currency']) == cstr(self.doc.currency):
				msgprint("Purchase Receipt: " + cstr(d.purchase_receipt) + " currency : " + cstr(data[0]['currency']) + " does not match with currency of current document.")
				raise Exception
			if not flt(data[0]['conversion_rate']) == flt(self.doc.conversion_rate):
				msgprint("Purchase Receipt: " + cstr(d.purchase_receipt) + " conversion_rate : " + cstr(data[0]['conversion_rate']) + " does not match with conversion_rate of current document.")
				raise Exception
					
	# Build tds table if applicable
	#------------------------------
	def get_tds(self):
		if cstr(self.doc.is_opening) != 'Yes':
			if not self.doc.credit_to:
				msgprint("Please Enter Credit To account first")
				raise Exception
			else:
				tds_applicable = sql("select tds_applicable from tabAccount where name = '%s'" % self.doc.credit_to)
				if tds_applicable and cstr(tds_applicable[0][0]) == 'Yes':
					if not self.doc.tds_applicable:
						msgprint("Please enter whether TDS Applicable or not")
						raise Exception
					if self.doc.tds_applicable == 'Yes':
						if not self.doc.tds_category:
							msgprint("Please select TDS Category")
							raise Exception
						else:
							get_obj('TDS Control').get_tds_amount(self)
							self.doc.total_tds_on_voucher = self.doc.ded_amount
							self.doc.total_amount_to_pay=flt(self.doc.grand_total)-flt(self.doc.ded_amount)-flt(self.doc.other_tax_deducted)
					elif self.doc.tds_applicable == 'No':
						self.doc.tds_category = ''
						self.doc.tax_code = ''
						self.doc.rate = 0
						self.doc.ded_amount = 0
						self.doc.total_tds_on_voucher = 0

	# get tds rate
	# -------------
	def get_tds_rate(self):
		return {'rate' : flt(get_value('Account', self.doc.tax_code, 'tax_rate'))}

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
	def set_against_expense_account(self):
		against_acc = []
		for d in getlist(self.doclist, 'entries'):
			if d.expense_account not in against_acc:
				against_acc.append(d.expense_account)
		self.doc.against_expense_account = ','.join(against_acc)

	#check in manage account if purchase order required or not.
	# ====================================================================================
	def po_required(self):
		res = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = 'po_required'")
		if res and res[0][0] == 'Yes':
			 for d in getlist(self.doclist,'entries'):
				 if not d.purchase_order:
					 msgprint("Purchse Order No. required against item %s"%d.item_code)
					 raise Exception

	#check in manage account if purchase receipt required or not.
	# ====================================================================================
	def pr_required(self):
		res = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = 'pr_required'")
		if res and res[0][0] == 'Yes':
			 for d in getlist(self.doclist,'entries'):
				 if not d.purchase_receipt:
					 msgprint("Purchase Receipt No. required against item %s"%d.item_code)
					 raise Exception

	# VALIDATE
	# ====================================================================================
	def validate(self):
		self.po_required()
		self.pr_required()
		self.check_active_purchase_items()
		self.check_conversion_rate()
		self.validate_bill_no_date()
		self.validate_bill_no()
		self.validate_reference_value()
		self.clear_advances()
		self.validate_credit_acc()
		self.check_for_acc_head_of_supplier()
		self.check_for_stopped_status()

		self.po_list, self.pr_list = [], []
		for d in getlist(self.doclist, 'entries'):
			self.validate_supplier(d)
			self.validate_po_pr(d)
			if not d.purchase_order in self.po_list:
				self.po_list.append(d.purchase_order)
			if not d.purhcase_receipt in self.pr_list:
				self.pr_list.append(d.purchase_receipt)
		# tds
		get_obj('TDS Control').validate_first_entry(self)
		if not flt(self.doc.ded_amount):
			self.get_tds()
			self.doc.save()

		if not self.doc.is_opening:
			self.doc.is_opening = 'No'

		self.set_aging_date()

		#set against account for credit to
		self.set_against_expense_account()

		#FY validation
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')
		
		#get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')
		
		 # get total in words
		self.doc.in_words = pc_obj.get_total_in_words('Rs', self.doc.grand_total)
		self.doc.in_words_import = pc_obj.get_total_in_words(self.doc.currency, self.doc.grand_total_import)
# ***************************** SUBMIT *****************************
	# Check Ref Document docstatus
	# -----------------------------
	def check_prev_docstatus(self):
		for d in getlist(self.doclist,'entries'):
			if d.purchase_order:
				submitted = sql("select name from `tabPurchase Order` where docstatus = 1 and name = '%s'" % d.purchase_order)
				if not submitted:
					msgprint("Purchase Order : "+ cstr(d.purchase_order) +" is not submitted")
					raise Exception , "Validation Error."
			if d.purchase_receipt:
				submitted = sql("select name from `tabPurchase Receipt` where docstatus = 1 and name = '%s'" % d.purchase_receipt)
				if not submitted:
					msgprint("Purchase Receipt : "+ cstr(d.purchase_receipt) +" is not submitted")
					raise Exception , "Validation Error."

	def update_against_document_in_jv(self, against_document_no, against_document_doctype):
		get_obj('GL Control').update_against_document_in_jv( self,'advance_allocation_details', against_document_no, against_document_doctype, self.doc.credit_to, 'debit',self.doc.doctype)

	# On Submit
	# ----------
	def on_submit(self):
		self.check_prev_docstatus()
		
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype,self.doc.company, self.doc.grand_total)
		
		
		# this sequence because outstanding may get -negative
		get_obj(dt='GL Control').make_gl_entries(self.doc, self.doclist)
		self.update_against_document_in_jv(self.doc.name, self.doc.doctype)
		get_obj(dt = 'Purchase Common').update_prevdoc_detail(self, is_submit = 1)



# ********************************* CANCEL *********************************
	# Check Next Document's docstatus
	# --------------------------------
	def check_next_docstatus(self):
		submit_jv = sql("select t1.name from `tabJournal Voucher` t1,`tabJournal Voucher Detail` t2 where t1.name = t2.parent and t2.against_voucher = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_jv:
			msgprint("Journal Voucher : " + cstr(submit_jv[0][0]) + " has been created against " + cstr(self.doc.doctype) + ". So " + cstr(self.doc.doctype) + " cannot be Cancelled.")
			raise Exception, "Validation Error."
		
	# On Cancel
	# ----------
	def on_cancel(self):
		self.check_next_docstatus()

		# Check whether tds payment voucher has been created against this voucher
		self.check_tds_payment_voucher()
		
		get_obj(dt='GL Control').make_gl_entries(self.doc, self.doclist, cancel=1)
		get_obj(dt = 'Purchase Common').update_prevdoc_detail(self, is_submit = 0)


	# Check whether tds payment voucher has been created against this voucher
	#---------------------------------------------------------------------------
	def check_tds_payment_voucher(self):
		tdsp =	sql("select parent from `tabTDS Payment Detail` where voucher_no = '%s' and docstatus = 1 and parent not like 'old%'")
		if tdsp:
			msgprint("TDS Payment voucher '%s' has been made against this voucher. Please cancel the payment voucher to proceed." % (tdsp and tdsp[0][0] or ''))
			raise Exception

	# on update
	def on_update(self):
		pass
		
########################################################################
# Repair Outstanding
#######################################################################
	def repair_pv_outstanding(self):
		get_obj(dt = 'GL Control').repair_voucher_outstanding(self)
