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


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.defaults = get_defaults()
		self.tname = 'Indent Detail'
		self.fname = 'indent_details'

	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')


	def get_default_schedule_date(self):
		get_obj(dt = 'Purchase Common').get_default_schedule_date(self)

	# Pull Sales Order Details
	# -------------------------
	def pull_so_details(self):
		self.check_if_already_pulled()
		if self.doc.sales_order_no:
			get_obj('DocType Mapper', 'Sales Order-Indent', with_children=1).dt_map('Sales Order', 'Indent', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Indent'],['Sales Order Detail', 'Indent Detail']]")
			self.get_item_defaults()
		else:
			msgprint("Please select Sales Order whose details need to pull")

	def check_if_already_pulled(self):
		pass#if self.[d.sales_order_no for d in getlist(self.doclist, 'indent_details')]


	# Get item's other details
	#- ------------------------
	def get_item_defaults(self):
		self.get_default_schedule_date()
		for d in getlist(self.doclist, 'indent_details'):
			det = sql("select min_order_qty from tabItem where name = '%s'" % d.item_code)
			d.min_order_qty = det and flt(det[0][0]) or 0

	# Validate so items
	# ----------------------------
	def validate_qty_against_so(self):
		so_items = {} # Format --> {'SO/00001': {'Item/001': 120, 'Item/002': 24}}
		for d in getlist(self.doclist, 'indent_details'):
			if d.sales_order_no:
				if not so_items.has_key(d.sales_order_no):
					so_items[d.sales_order_no] = {d.item_code: flt(d.qty)}
				else:
					if not so_items[d.sales_order_no].has_key(d.item_code):
						so_items[d.sales_order_no][d.item_code] = flt(d.qty)
					else:
						so_items[d.sales_order_no][d.item_code] += flt(d.qty)
		
		for so_no in so_items.keys():
			for item in so_items[so_no].keys():
				already_indented = sql("select sum(qty) from `tabIndent Detail` where item_code = '%s' and sales_order_no = '%s' and docstatus = 1 and parent != '%s'" % (item, so_no, self.doc.name))
				already_indented = already_indented and flt(already_indented[0][0]) or 0
				
				actual_so_qty = sql("select sum(qty) from `tabSales Order Detail` where parent = '%s' and item_code = '%s' and docstatus = 1 group by parent" % (so_no, item))
				actual_so_qty = actual_so_qty and flt(actual_so_qty[0][0]) or 0

				if flt(so_items[so_no][item]) + already_indented > actual_so_qty:
					msgprint("You can raise indent of maximum qty: %s for item: %s against sales order: %s\n Anyway, you can add more qty in new row for the same item." % (actual_so_qty - already_indented, item, so_no), raise_exception=1)
				
		
	# Validate fiscal year
	# ----------------------------
	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'Indent Date')

	# get item details
	# ---------------------------------
	def get_item_details(self, arg =''):
		return get_obj(dt='Purchase Common').get_item_details(self,arg)

	# Get UOM Details
	# ---------------------------------
	def get_uom_details(self, arg = ''):
		return get_obj(dt='Purchase Common').get_uom_details(arg)

	# GET TERMS & CONDITIONS
	#-----------------------------
	def get_tc_details(self):
		return get_obj('Purchase Common').get_tc_details(self)
		
	# Validate Schedule Date
	#--------------------------------
	def validate_schedule_date(self):
		 #:::::::: validate schedule date v/s indent date ::::::::::::
		for d in getlist(self.doclist, 'indent_details'):
			if d.schedule_date < self.doc.transaction_date:
				msgprint("Expected Schedule Date cannot be before Indent Date")
				raise Exception
				
	# Validate
	# ---------------------
	def validate(self):
		self.validate_schedule_date()
		self.validate_fiscal_year()
		
		# set status as "Draft"
		set(self.doc, 'status', 'Draft')

		# Get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')

		# Validate Mandatory
		pc_obj.validate_mandatory(self)

		# Validate for items
		pc_obj.validate_for_items(self)
		
		# Validate qty against SO
		self.validate_qty_against_so()


	# On Submit Functions
	#----------------------------------------------------------------------------
	
	# Update Indented Qty in Bin
	def update_bin(self, is_submit, is_stopped):
		for d in getlist(self.doclist, 'indent_details'):
			# Step 1:=> Check if is_stock_item == 'Yes'
			if cstr(sql("select is_stock_item from `tabItem` where name = '%s'" % cstr(d.item_code))[0][0]) == 'Yes':
				if not d.warehouse:
					msgprint('Please Enter Warehouse for Item %s as it is stock item.' % cstr(d.item_code))
					raise Exception
				# Step 2:=> Set Qty 
				qty =flt(d.qty)
				if is_stopped:
					qty = (d.qty > d.ordered_qty) and flt(flt(d.qty) - flt(d.ordered_qty)) or 0 
				# Step 3 :=> Update Bin's Indent Qty by +- qty 
				get_obj('Warehouse', d.warehouse).update_bin(0, 0, 0, (is_submit and 1 or -1) * flt(qty), 0, d.item_code, self.doc.transaction_date)		
		
	# On Submit			
	#---------------------------------------------------------------------------
	def on_submit(self):
		# Step 1:=> Set Status
		set(self.doc,'status','Submitted')

		# Step 2:=> Update Bin
		self.update_bin(is_submit = 1, is_stopped = 0)
	
	def check_modified_date(self):
		mod_db = sql("select modified from `tabIndent` where name = '%s'" % self.doc.name)
		date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
		
		if date_diff and date_diff[0][0]:
			msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
			raise Exception
	
	# On Stop / unstop
	#------------------------------------------------------------------------------
	def update_status(self, status):
		self.check_modified_date()
		# Step 1:=> Update Bin
		self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

		# Step 2:=> Set status 
		set(self.doc,'status',cstr(status))
		
		# Step 3:=> Acknowledge User
		msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)) )
 
	# On Cancel
	#-----------------------------------------------------------------------------
	def on_cancel(self):
		# Step 1:=> Get Purchase Common Obj
		pc_obj = get_obj(dt='Purchase Common')
		
		# Step 2:=> Check for stopped status
		pc_obj.check_for_stopped_status( self.doc.doctype, self.doc.name)
		
		# Step 3:=> Check if Purchase Order has been submitted against current Indent
		pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.doc.name, detail_doctype = 'PO Detail')
		# Step 4:=> Update Bin
		self.update_bin(is_submit = 0, is_stopped = (cstr(self.doc.status) == 'Stopped') and 1 or 0)
		
		# Step 5:=> Set Status
		set(self.doc,'status','Cancelled')


	# Repair Indent
	# ===========================================
	def repair_indent(self):
		get_obj('Purchase Common', 'Purchase Common').repair_curr_doctype_details(self)
