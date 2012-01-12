# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

		self.doctype_dict = {
			'Sales Order'		: 'Sales Order Detail',
			'Delivery Note'		: 'Delivery Note Detail',
			'Receivable Voucher':'RV Detail',
			'Installation Note' : 'Installed Item Details'
		}
												 
		self.ref_doctype_dict= {}

		self.next_dt_detail = {
			'delivered_qty' : 'Delivery Note Detail',
			'billed_qty'		: 'RV Detail',
			'installed_qty' : 'Installed Item Details'}

		self.msg = []


	# Get Sales Person Details
	# ==========================
	def get_sales_person_details(self, obj):
		if obj.doc.doctype != 'Quotation':
			obj.doc.clear_table(obj.doclist,'sales_team')
			idx = 0
			for d in sql("select sales_person, allocated_percentage, allocated_amount, incentives from `tabSales Team` where parent = '%s'" % obj.doc.customer):
				ch = addchild(obj.doc, 'sales_team', 'Sales Team', 1, obj.doclist)
				ch.sales_person = d and cstr(d[0]) or ''
				ch.allocated_percentage = d and flt(d[1]) or 0
				ch.allocated_amount = d and flt(d[2]) or 0
				ch.incentives = d and flt(d[3]) or 0
				ch.idx = idx
				idx += 1


	# Get customer's contact person details
	# ==============================================================
	def get_contact_details(self, obj = '', primary = 0):
		cond = " and contact_name = '"+cstr(obj.doc.contact_person)+"'"
		if primary: cond = " and is_primary_contact = 'Yes'"
		contact = sql("select contact_name, contact_no, email_id, contact_address from `tabContact` where customer = '%s' and docstatus != 2 %s" %(obj.doc.customer, cond), as_dict = 1)
		if not contact:
			return
		c = contact[0]
		obj.doc.contact_person = c['contact_name'] or ''
		obj.doc.contact_no = c['contact_no'] or ''
		obj.doc.email_id = c['email_id'] or ''
		obj.doc.customer_mobile_no = c['contact_no'] or ''
		if c['contact_address']:
			obj.doc.customer_address = c['contact_address']


	# Get customer's primary shipping details
	# ==============================================================
	def get_shipping_details(self, obj = ''):
		det = sql("select name, ship_to, shipping_address from `tabShipping Address` where customer = '%s' and docstatus != 2 and ifnull(is_primary_address, 'Yes') = 'Yes'" %(obj.doc.customer), as_dict = 1)
		obj.doc.ship_det_no = det and det[0]['name'] or ''
		obj.doc.ship_to = det and det[0]['ship_to'] or ''
		obj.doc.shipping_address = det and det[0]['shipping_address'] or ''


	# get invoice details
	# ====================
	def get_invoice_details(self, obj = ''):
		if obj.doc.company:
			acc_head = sql("select name from `tabAccount` where name = '%s' and docstatus != 2" % (cstr(obj.doc.customer) + " - " + get_value('Company', obj.doc.company, 'abbr')))
			obj.doc.debit_to = acc_head and acc_head[0][0] or ''


	# Get Customer Details along with its primary contact details
	# ==============================================================
	def get_customer_details(self, obj = '', inv_det_reqd = 1):
		details = sql("select customer_name,address, territory, customer_group, default_sales_partner, default_commission_rate from `tabCustomer` where name = '%s' and docstatus != 2" %(obj.doc.customer), as_dict = 1)
		obj.doc.customer_name = details and details[0]['customer_name'] or ''
		obj.doc.customer_address =	details and details[0]['address'] or ''
		obj.doc.territory = details and details[0]['territory'] or ''
		obj.doc.customer_group	=	details and details[0]['customer_group'] or ''
		obj.doc.sales_partner	 =	details and details[0]['default_sales_partner'] or ''
		obj.doc.commission_rate =	details and flt(details[0]['default_commission_rate']) or ''
		if obj.doc.doctype != 'Receivable Voucher':
			obj.doc.delivery_address =	details and details[0]['address'] or ''
			self.get_contact_details(obj,primary = 1) # get primary contact details
		self.get_sales_person_details(obj) # get default sales person details

		if obj.doc.doctype == 'Receivable Voucher' and inv_det_reqd:
			self.get_invoice_details(obj) # get invoice details
	
	
	# Get Item Details
	# ===============================================================
	def get_item_details(self, item_code, obj):
		if not obj.doc.price_list_name:
			msgprint("Please Select Price List before selecting Items")
			raise Exception
		item = sql("select description, item_name, brand, item_group, stock_uom, default_warehouse, default_income_account, default_sales_cost_center, description_html from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life >	now() or end_of_life = '0000-00-00') and (is_sales_item = 'Yes' or is_service_item = 'Yes')" %(item_code), as_dict=1)
		tax = sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , item_code)
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'description'			: item and item[0]['description_html'] or item[0]['description'],
			'item_group'			: item and item[0]['item_group'] or '',
			'item_name'				: item and item[0]['item_name'] or '',
			'brand'					: item and item[0]['brand'] or '',
			'stock_uom'				: item and item[0]['stock_uom'] or '',
			'reserved_warehouse'	: item and item[0]['default_warehouse'] or '',
			'warehouse'				: item and item[0]['default_warehouse'] or '',
			'income_account'		: item and item[0]['default_income_account'] or '',
			'cost_center'			: item and item[0]['default_sales_cost_center'] or '',
			'qty'					: 1.00,	 # this is done coz if item once fetched is fetched again thn its qty shld be reset to 1
			'adj_rate'				: 0,
			'amount'				: 0,
			'export_amount'			: 0,
			'item_tax_rate'			: str(t),
			'batch_no'				: ''
		}
		if(obj.doc.price_list_name and item):	#this is done to fetch the changed BASIC RATE and REF RATE based on PRICE LIST
			base_ref_rate =	self.get_ref_rate(item_code, obj.doc.price_list_name, obj.doc.price_list_currency, obj.doc.plc_conversion_rate)
			ret['ref_rate'] = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			ret['export_rate'] = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			ret['base_ref_rate'] = flt(base_ref_rate)
			ret['basic_rate'] = flt(base_ref_rate)

		return ret
	
	# ***************** Get Ref rate as entered in Item Master ********************
	def get_ref_rate(self, item_code, price_list_name, price_list_currency, plc_conv_rate):
		ref_rate = sql("select ref_rate from `tabRef Rate Detail` where parent = %s and price_list_name = %s and ref_currency = %s", (item_code, price_list_name, price_list_currency))
		base_ref_rate = ref_rate and flt(ref_rate[0][0]) * flt(plc_conv_rate) or 0
		return base_ref_rate

		
	# ****** Re-cancellculates Basic Rate & amount based on Price List Selected ******
	def get_adj_percent(self, obj): 
		for d in getlist(obj.doclist, obj.fname):
			base_ref_rate = self.get_ref_rate(d.item_code, obj.doc.price_list_name, obj.doc.price_list_currency, obj.doc.plc_conversion_rate)
			d.adj_rate = 0
			d.ref_rate = flt(base_ref_rate)/flt(obj.doc.conversion_rate)
			d.basic_rate = flt(base_ref_rate)
			d.base_ref_rate = flt(base_ref_rate)
			d.export_rate = flt(base_ref_rate)/flt(obj.doc.conversion_rate)


	# Load Default Taxes
	# ====================
	def load_default_taxes(self, obj):
		self.get_other_charges(obj,1)

		
	# Get other charges from Master
	# =================================================================================
	def get_other_charges(self,obj,default = 0):
		obj.doc.clear_table(obj.doclist,'other_charges')
		if not getlist(obj.doclist, 'other_charges'):
			if default: add_cond = 'ifnull(t2.is_default,0) = 1'
			else: add_cond = 't1.parent = "'+cstr(obj.doc.charge)+'"'
			idx = 0
			other_charge = sql("select t1.charge_type,t1.row_id,t1.description,t1.account_head,t1.rate,t1.tax_amount,t1.included_in_print_rate from `tabRV Tax Detail` t1, `tabOther Charges` t2 where t1.parent = t2.name and t2.company = '%s' and %s order by t1.idx" % (obj.doc.company, add_cond), as_dict = 1)
			for other in other_charge:
				d =	addchild(obj.doc, 'other_charges', 'RV Tax Detail', 1, obj.doclist)
				d.charge_type = other['charge_type']
				d.row_id = other['row_id']
				d.description = other['description']
				d.account_head = other['account_head']
				d.rate = flt(other['rate'])
				d.tax_amount = flt(other['tax_amount'])
				d.included_in_print_rate = cint(other['included_in_print_rate'])
				d.idx = idx
				idx += 1
			
			
	# Get TERMS AND CONDITIONS
	# =======================================================================================
	def get_tc_details(self,obj):
		r = sql("select terms from `tabTerm` where name = %s", obj.doc.tc_name)
		if r: obj.doc.terms = r[0][0]

#---------------------------------------- Get Tax Details -------------------------------#
	def get_tax_details(self, item_code, obj):
		tax = sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , item_code)
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'item_tax_rate'		:	tax and str(t) or ''
		}
		return ret

	# Get Serial No Details
	# ==========================================================================
	def get_serial_details(self, serial_no, obj):
		item = sql("select item_code, make, label,brand, description from `tabSerial No` where name = '%s' and docstatus != 2" %(serial_no), as_dict=1)
		tax = sql("select tax_type, tax_rate from `tabItem Tax` where parent = %s" , item[0]['item_code'])
		t = {}
		for x in tax: t[x[0]] = flt(x[1])
		ret = {
			'item_code'				: item and item[0]['item_code'] or '',
			'make'						 : item and item[0]['make'] or '',
			'label'						: item and item[0]['label'] or '',
			'brand'						: item and item[0]['brand'] or '',
			'description'			: item and item[0]['description'] or '',
			'item_tax_rate'		: str(t)
		}
		return ret
		
	# Get Commission rate
	# =======================================================================
	def get_comm_rate(self, sales_partner, obj):

		comm_rate = sql("select commission_rate from `tabSales Partner` where name = '%s' and docstatus != 2" %(sales_partner), as_dict=1)
		if comm_rate:
			total_comm = flt(comm_rate[0]['commission_rate']) * flt(obj.doc.net_total) / 100
			ret = {
				'commission_rate'		 :	comm_rate and flt(comm_rate[0]['commission_rate']) or 0,
				'total_commission'		:	flt(total_comm)
			}
			return ret
		else:
			msgprint("Business Associate : %s does not exist in the system." % (sales_partner))
			raise Exception

	
	# To verify whether rate entered in details table does not exceed max discount %
	# =======================================================================================
	def validate_max_discount(self,obj, detail_table):
		for d in getlist(obj.doclist, detail_table):
			discount = sql("select max_discount from tabItem where name = '%s'" %(d.item_code),as_dict = 1)
			if discount and discount[0]['max_discount'] and (flt(d.adj_rate)>flt(discount[0]['max_discount'])):
				msgprint("You cannot give more than " + cstr(discount[0]['max_discount']) + " % discount on Item Code : "+cstr(d.item_code))
				raise Exception


	# Get sum of allocated % of sales person (it should be 100%)
	# ========================================================================
	# it indicates % contribution of sales person in sales
	def get_allocated_sum(self,obj):
		sum = 0
		for d in getlist(obj.doclist,'sales_team'):
			sum += flt(d.allocated_percentage)
		if (flt(sum) != 100) and getlist(obj.doclist,'sales_team'):
			msgprint("Total Allocated % of Sales Persons should be 100%")
			raise Exception
			
	# Check Conversion Rate (i.e. it will not allow conversion rate to be 1 for Currency other than default currency set in Global Defaults)
	# ===========================================================================
	def check_conversion_rate(self, obj):
		default_currency = TransactionBase().get_company_currency(obj.doc.company)
		if not default_currency:
			msgprint('Message: Please enter default currency in Company Master')
			raise Exception		
		if (obj.doc.currency == default_currency and flt(obj.doc.conversion_rate) != 1.00) or not obj.doc.conversion_rate or (obj.doc.currency != default_currency and flt(obj.doc.conversion_rate) == 1.00):
			msgprint("Please Enter Appropriate Conversion Rate for Customer's Currency to Base Currency (%s --> %s)" % (obj.doc.currency, default_currency), raise_exception = 1)
	
		if (obj.doc.price_list_currency == default_currency and flt(obj.doc.plc_conversion_rate) != 1.00) or not obj.doc.plc_conversion_rate or (obj.doc.price_list_currency != default_currency and flt(obj.doc.plc_conversion_rate) == 1.00):
			msgprint("Please Enter Appropriate Conversion Rate for Price List Currency to Base Currency ( (%s --> %s)" % (obj.doc.price_list_currency, default_currency), raise_exception = 1)
	


	# Get Tax rate if account type is TAX
	# =========================================================================
	def get_rate(self, arg):
		arg = eval(arg)
		rate = sql("select account_type, tax_rate from `tabAccount` where name = '%s' and docstatus != 2" %(arg['account_head']), as_dict=1)
		ret = {'rate' : 0}
		if arg['charge_type'] == 'Actual' and rate[0]['account_type'] == 'Tax':
			msgprint("You cannot select ACCOUNT HEAD of type TAX as your CHARGE TYPE is 'ACTUAL'")
			ret = {
				'account_head'	:	''
			}
		elif rate[0]['account_type'] in ['Tax', 'Chargeable'] and not arg['charge_type'] == 'Actual':
			ret = {
				'rate'	:	rate and flt(rate[0]['tax_rate']) or 0
			}
		return ret
		

	# Make Packing List from Sales BOM
	# =======================================================================
	def has_sales_bom(self, item_code):
		return sql("select name from `tabSales BOM` where name=%s and docstatus != 2", item_code)
	
	def get_sales_bom_items(self, item_code):
		return sql("select item_code, qty, uom from `tabSales BOM Detail` where parent=%s", item_code)


	# --------------
	# get item list
	# --------------
	def get_item_list(self, obj, is_stopped):
		il = []
		for d in getlist(obj.doclist,obj.fname):
			reserved_qty = 0		# used for delivery note
			qty = flt(d.qty)
			if is_stopped:
				qty = flt(d.qty) > flt(d.delivered_qty) and flt(flt(d.qty) - flt(d.delivered_qty)) or 0
				
			if d.prevdoc_doctype == 'Sales Order':			# used in delivery note to reduce reserved_qty 
				# Eg.: if SO qty is 10 and there is tolerance of 20%, then it will allow DN of 12.
				# But in this case reserved qty should only be reduced by 10 and not 12.

				tot_qty, max_qty, tot_amt, max_amt = self.get_curr_and_ref_doc_details(d.doctype, 'prevdoc_detail_docname', d.prevdoc_detail_docname, 'Sales Order Detail', obj.doc.name, obj.doc.doctype)
				if((flt(tot_qty) + flt(qty) > flt(max_qty))):
					reserved_qty = -(flt(max_qty)-flt(tot_qty))
				else:	
					reserved_qty = - flt(qty)
			
			warehouse = (obj.fname == "sales_order_details") and d.reserved_warehouse or d.warehouse
			
			if self.has_sales_bom(d.item_code):
				for i in self.get_sales_bom_items(d.item_code):
					il.append([warehouse, i[0], flt(flt(i[1])* qty), flt(flt(i[1])*reserved_qty), i[2], d.batch_no, d.serial_no])
			else:
				il.append([warehouse, d.item_code, qty, reserved_qty, d.stock_uom, d.batch_no, d.serial_no])
		return il

	# ---------------------------------------------------------------------------------------------
	# get qty, amount already billed or delivered against curr line item for current doctype
	# For Eg: SO-RV get total qty, amount from SO and also total qty, amount against that SO in RV
	# ---------------------------------------------------------------------------------------------
	def get_curr_and_ref_doc_details(self, curr_doctype, ref_tab_fname, ref_tab_dn, ref_doc_tname, curr_parent_name, curr_parent_doctype):
		# Get total qty, amt of current doctype (eg RV) except for qty, amt of this transaction
		if curr_parent_doctype == 'Installation Note':
			curr_det = sql("select sum(qty) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% (curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
			qty, amt = curr_det and flt(curr_det[0][0]) or 0, 0
		else:
			curr_det = sql("select sum(qty), sum(amount) from `tab%s` where %s = '%s' and docstatus = 1 and parent != '%s'"% (curr_doctype, ref_tab_fname, ref_tab_dn, curr_parent_name))
			qty, amt = curr_det and flt(curr_det[0][0]) or 0, curr_det and flt(curr_det[0][1]) or 0

		# get total qty of ref doctype
		ref_det = sql("select qty, amount from `tab%s` where name = '%s' and docstatus = 1"% (ref_doc_tname, ref_tab_dn))
		max_qty, max_amt = ref_det and flt(ref_det[0][0]) or 0, ref_det and flt(ref_det[0][1]) or 0

		return qty, max_qty, amt, max_amt





	# -----------------------
	# add packing list items
	# -----------------------
	def get_packing_item_details(self, item):
		return sql("select item_name, description, stock_uom from `tabItem` where name = %s", item, as_dict = 1)[0]

	def get_bin_qty(self, item, warehouse):
		det = sql("select actual_qty, projected_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (item, warehouse), as_dict = 1)
		return det and det[0] or ''

	def add_packing_list_item(self,obj, item_code, qty, warehouse, line):
		bin = self.get_bin_qty(item_code, warehouse)
		item = self.get_packing_item_details(item_code)
		pi = addchild(obj.doc, 'packing_details', 'Delivery Note Packing Detail', 1, obj.doclist)
		pi.parent_item = item_code
		pi.item_code = item_code
		pi.item_name = item['item_name']
		pi.parent_detail_docname = line.name
		pi.description = item['description']
		pi.uom = item['stock_uom']
		pi.qty = flt(qty)
		pi.actual_qty = bin and flt(bin['actual_qty']) or 0
		pi.projected_qty = bin and flt(bin['projected_qty']) or 0
		pi.warehouse = warehouse
		pi.prevdoc_doctype = line.prevdoc_doctype
		pi.serial_no = cstr(line.serial_no)
		pi.idx = self.packing_list_idx
		self.packing_list_idx += 1


	# ------------------
	# make packing list from sales bom if exists or directly copy item with balance
	# ------------------ 
	def make_packing_list(self, obj, fname):
		obj.doc.clear_table(obj.doclist, 'packing_details')
		self.packing_list_idx = 0
		for d in getlist(obj.doclist, fname):
			warehouse = fname == "sales_order_details" and d.reserved_warehouse or d.warehouse
			if self.has_sales_bom(d.item_code):
				for i in self.get_sales_bom_items(d.item_code):
					self.add_packing_list_item(obj, i[0], flt(i[1])*flt(d.qty), warehouse, d)
			else:
				self.add_packing_list_item(obj, d.item_code, d.qty, warehouse, d)


	# Get total in words
	# ==================================================================	
	def get_total_in_words(self, currency, amount):
		from webnotes.utils import money_in_words
		return money_in_words(amount, currency)
		

	# Get month based on date (required in sales person and sales partner)
	# ========================================================================
	def get_month(self,date):
		month_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
		month_idx = cint(cstr(date).split('-')[1])-1
		return month_list[month_idx]
		
		
	# **** Check for Stop SO as no transactions can be made against Stopped SO. Need to unstop it. ***
	def check_stop_sales_order(self,obj):
		for d in getlist(obj.doclist,obj.fname):
			ref_doc_name = ''
			if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_doctype == 'Sales Order':
				ref_doc_name = d.prevdoc_docname
			elif d.fields.has_key('sales_order') and d.sales_order and not d.delivery_note:
				ref_doc_name = d.sales_order
			if ref_doc_name:
				so_status = sql("select status from `tabSales Order` where name = %s",ref_doc_name)
				so_status = so_status and so_status[0][0] or ''
				if so_status == 'Stopped':
					msgprint("You cannot do any transaction against Sales Order : '%s' as it is Stopped." %(ref_doc_name))
					raise Exception
					
					
	# ****** Check for Item.is_sales_item = 'Yes' and Item.docstatus != 2 *******
	def check_active_sales_items(self,obj):
		for d in getlist(obj.doclist, obj.fname):
			if d.item_code:		# extra condn coz item_code is not mandatory in RV
				valid_item = sql("select docstatus,is_sales_item, is_service_item from tabItem where name = %s",d.item_code)
				if valid_item and valid_item[0][0] == 2:
					msgprint("Item : '%s' does not exist in system." %(d.item_code))
					raise Exception
				sales_item = valid_item and valid_item[0][1] or 'No'
				service_item = valid_item and valid_item[0][2] or 'No'
				if sales_item == 'No' and service_item == 'No':
					msgprint("Item : '%s' is neither Sales nor Service Item"%(d.item_code))
					raise Exception


# **************************************************************************************************************************************************

	def check_credit(self,obj,grand_total):
		acc_head = sql("select name from `tabAccount` where company = '%s' and master_name = '%s'"%(obj.doc.company, obj.doc.customer))
		if acc_head:
			tot_outstanding = 0
			dbcr = sql("select sum(debit), sum(credit) from `tabGL Entry` where account = '%s' and ifnull(is_cancelled, 'No')='No'" % acc_head[0][0])
			if dbcr:
				tot_outstanding = flt(dbcr[0][0])-flt(dbcr[0][1])

			exact_outstanding = flt(tot_outstanding) + flt(grand_total)
			get_obj('Account',acc_head[0][0]).check_credit_limit(acc_head[0][0], obj.doc.company, exact_outstanding)

	def validate_fiscal_year(self,fiscal_year,transaction_date,dn):
		fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%fiscal_year)
		ysd=fy and fy[0][0] or ""
		yed=add_days(str(ysd),365)
		if str(transaction_date) < str(ysd) or str(transaction_date) > str(yed):
			msgprint("%s not within the fiscal year"%(dn))
			raise Exception


	# get against document date	self.prevdoc_date_field
	#-----------------------------
	def get_prevdoc_date(self, obj):
		import datetime
		for d in getlist(obj.doclist, obj.fname):
			if d.prevdoc_doctype and d.prevdoc_docname:
				if d.prevdoc_doctype == 'Receivable Voucher':
					dt = sql("select posting_date from `tab%s` where name = '%s'" % (d.prevdoc_doctype, d.prevdoc_docname))
				else:
					dt = sql("select transaction_date from `tab%s` where name = '%s'" % (d.prevdoc_doctype, d.prevdoc_docname))
				d.prevdoc_date = dt and dt[0][0].strftime('%Y-%m-%d') or ''

	def update_prevdoc_detail(self, is_submit, obj):
		StatusUpdater(obj, is_submit).update()




#
# make item code readonly if (detail no is set)
#


class StatusUpdater:
	"""
		Updates the status of the calling records
		
		From Delivery Note 
			- Update Delivered Qty
			- Update Percent
			- Validate over delivery
			
		From Receivable Voucher 
			- Update Billed Amt
			- Update Percent
			- Validate over billing
			
		From Installation Note
			- Update Installed Qty
			- Update Percent Qty
			- Validate over installation
	"""
	def __init__(self, obj, is_submit):
		self.obj = obj # caller object
		self.is_submit = is_submit
		self.tolerance = {}
		self.global_tolerance = None
	
	def update(self):
		self.update_all_qty()
		self.validate_all_qty()
	
	def validate_all_qty(self):
		"""
			Validates over-billing / delivery / installation in Delivery Note, Receivable Voucher, Installation Note
			To called after update_all_qty
		"""
		if self.obj.doc.doctype=='Delivery Note':
			self.validate_qty({
				'source_dt'		:'Delivery Note Detail',
				'compare_field'	:'delivered_qty',
				'compare_ref_field'	:'qty',
				'target_dt'		:'Sales Order Detail',
				'join_field'	:'prevdoc_detail_docname'
			})
		elif self.obj.doc.doctype=='Receivable Voucher':
			self.validate_qty({
				'source_dt'		:'RV Detail',
				'compare_field'	:'billed_amt',
				'compare_ref_field'	:'amount',
				'target_dt'		:'Sales Order Detail',
				'join_field'	:'so_detail'
			})
			self.validate_qty({
				'source_dt'		:'RV Detail',
				'compare_field'	:'billed_amt',
				'compare_ref_field'	:'amount',
				'target_dt'		:'Delivery Note Detail',
				'join_field'	:'dn_detail'
			}, no_tolerance =1)
		elif self.obj.doc.doctype=='Installation Note':
			self.validate_qty({
				'source_dt'		:'Installation Item Details',
				'compare_field'	:'installed_qty',
				'compare_ref_field'	:'qty',
				'target_dt'		:'Delivery Note Detail',
				'join_field'	:'dn_detail'
			}, no_tolerance =1)

	
	def get_tolerance_for(self, item_code):
		"""
			Returns the tolerance for the item, if not set, returns global tolerance
		"""
		if self.tolerance.get(item_code):
			return self.tolerance[item_code]
		
		tolerance = flt(get_value('Item',item_code,'tolerance') or 0)

		if not(tolerance):
			if self.global_tolerance == None:
				self.global_tolerance = flt(get_value('Manage Account',None,'tolerance') or 0)
			tolerance = self.global_tolerance
		
		self.tolerance[item_code] = tolerance
		return tolerance
		
	def check_overflow_with_tolerance(self, item, args):
		"""
			Checks if there is overflow condering a relaxation tolerance
		"""
	
		# check if overflow is within tolerance
		tolerance = self.get_tolerance_for(item['item_code'])
		overflow_percent = ((item[args['compare_field']] - item[args['compare_ref_field']]) / item[args['compare_ref_field']] * 100)
	
		if overflow_percent - tolerance > 0.0001:
			item['max_allowed'] = flt(item[args['compare_ref_field']] * (100+tolerance)/100)
			item['reduce_by'] = item[args['compare_field']] - item['max_allowed']
		
			msgprint("""
				Row #%(idx)s: Max %(compare_ref_field)s allowed for <b>Item %(item_code)s</b> against <b>%(parenttype)s %(parent)s</b> is <b>%(max_allowed)s</b>. 
				
				If you want to increase your overflow tolerance, please increase tolerance %% in Global Defaults or Item master. 
				
				Or, you must reduce the %(compare_ref_field)s by %(reduce_by)s""" % item, raise_exception=1)

	def validate_qty(self, args, no_tolerance=None):
		"""
			Validates qty at row level
		"""
		# get unique transactions to update
		for d in self.obj.doclist:
			if d.doctype == args['source_dt']:
				args['name'] = d.fields[args['join_field']]

				# get all qty where qty > compare_field
				item = sql("""
					select item_code, `%(compare_ref_field)s`, `%(compare_field)s`, parenttype, parent from `tab%(target_dt)s` 
					where `%(compare_ref_field)s` < `%(compare_field)s` and name="%(name)s" and docstatus=1
					""" % args, as_dict=1)
				if item:
					item = item[0]
					item['idx'] = d.idx
					item['compare_ref_field'] = args['compare_ref_field']

					if not item[args['compare_ref_field']]:
						msgprint("As %(compare_ref_field)s for item: %(item_code)s in %(parenttype)s: %(parent)s is zero, system will not check over-delivery or over-billed" % item)
					elif no_tolerance:
						item['reduce_by'] = item[args['compare_field']] - item[args['compare_ref_field']]
						msgprint("""
							Row #%(idx)s: Max %(compare_ref_field)s allowed for <b>Item %(item_code)s</b> against 
							<b>%(parenttype)s %(parent)s</b> is <b>""" % item 
							+ cstr(item[args['compare_ref_field']]) + """</b>. 
							
							You must reduce the %(compare_ref_field)s by %(reduce_by)s""" % item, raise_exception=1)
					
					else:
						self.check_overflow_with_tolerance(item, args)
						
	
	def update_all_qty(self):
		"""
			Updates delivered / billed / installed qty in Sales Order & Delivery Note
		"""
		if self.obj.doc.doctype=='Delivery Note':
			self.update_qty({
				'target_field'			:'delivered_qty',
				'target_dt'				:'Sales Order Detail',
				'target_parent_dt'		:'Sales Order',
				'target_parent_field'	:'per_delivered',
				'target_ref_field'		:'qty',
				'source_dt'				:'Delivery Note Detail',
				'source_field'			:'qty',
				'join_field'			:'prevdoc_detail_docname',
				'percent_join_field'	:'prevdoc_docname',
				'status_field'			:'delivery_status',
				'keyword'				:'Delivered'
			})
			
		elif self.obj.doc.doctype=='Receivable Voucher':
			self.update_qty({
				'target_field'			:'billed_amt',
				'target_dt'				:'Sales Order Detail',
				'target_parent_dt'		:'Sales Order',
				'target_parent_field'	:'per_billed',
				'target_ref_field'		:'amount',
				'source_dt'				:'RV Detail',
				'source_field'			:'amount',
				'join_field'			:'so_detail',
				'percent_join_field'	:'sales_order',
				'status_field'			:'billing_status',
				'keyword'				:'Billed'
			})

			self.update_qty({
				'target_field'			:'billed_amt',
				'target_dt'				:'Delivery Note Detail',
				'target_parent_dt'		:'Delivery Note',
				'target_parent_field'	:'per_billed',
				'target_ref_field'		:'amount',
				'source_dt'				:'RV Detail',
				'source_field'			:'amount',
				'join_field'			:'dn_detail',
				'percent_join_field'	:'delivery_note',
				'status_field'			:'billing_status',
				'keyword'				:'Billed'
			})

		if self.obj.doc.doctype=='Installation Note':
			self.update_qty({
				'target_field'			:'installed_qty',
				'target_dt'				:'Delivery Note Detail',
				'target_parent_dt'		:'Delivery Note',
				'target_parent_field'	:'per_installed',
				'target_ref_field'		:'qty',
				'source_dt'				:'Installed Item Details',
				'source_field'			:'qty',
				'join_field'			:'prevdoc_detail_docname',
				'percent_join_field'	:'prevdoc_docname',
				'status_field'			:'installation_status',
				'keyword'				:'Installed'
			})


	def update_qty(self, args):
		"""
			Updates qty at row level
		"""
		# condition to include current record (if submit or no if cancel)
		if self.is_submit:
			args['cond'] = ' or parent="%s"' % self.obj.doc.name
		else:
			args['cond'] = ' and parent!="%s"' % self.obj.doc.name
		
		# update quantities in child table
		for d in self.obj.doclist:
			if d.doctype == args['source_dt']:
				# updates qty in the child table
				args['detail_id'] = d.fields.get(args['join_field'])
			
				if args['detail_id']:
					sql("""
						update 
							`tab%(target_dt)s` 
						set 
							%(target_field)s = (select sum(%(source_field)s) from `tab%(source_dt)s` where `%(join_field)s`="%(detail_id)s" and (docstatus=1 %(cond)s))
						where
							name="%(detail_id)s"            
					""" % args)			
		
		# get unique transactions to update
		for name in set([d.fields.get(args['percent_join_field']) for d in self.obj.doclist if d.doctype == args['source_dt']]):
			if name:
				args['name'] = name
				
				# update percent complete in the parent table
				sql("""
					update 
						`tab%(target_parent_dt)s` 
					set 
						%(target_parent_field)s = 
							(select sum(if(%(target_ref_field)s > ifnull(%(target_field)s, 0), %(target_field)s, %(target_ref_field)s))/sum(%(target_ref_field)s)*100 from `tab%(target_dt)s` where parent="%(name)s"), 
						modified = now()
					where
						name="%(name)s"
					""" % args)

				# update field
				if args['status_field']:
					sql("""
						update
							`tab%(target_parent_dt)s` 
						set
							%(status_field)s = if(ifnull(%(target_parent_field)s,0)<0.001, 'Not %(keyword)s', 
									if(%(target_parent_field)s>=99.99, 'Fully %(keyword)s', 'Partly %(keyword)s')
								)
						where
							name="%(name)s"
					""" % args)
