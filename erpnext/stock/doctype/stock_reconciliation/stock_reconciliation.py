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
		self.label = { 'item_code': 0 , 'warehouse': 1 , 'qty': 2, 'mar': 3,'stock_uom':4, 'actual_qty':5, 'diff': 6} # with mar

	# autoname
	#-----------------
	def autoname(self):
		 self.doc.name = make_autoname('SR/' + self.doc.fiscal_year + '/.######')

	# -----------------
	# update next step
	# -----------------
	def update_next_step(self,next_step):
		sql("update `tabStock Reconciliation` set next_step = '%s' where name = '%s'" % (next_step,self.doc.name))
	

	# -----------
	# add remark
	# -----------
	def add_remark(self, text, next_step, first_time = 0):
		if first_time:
			sql("update `tabStock Reconciliation` set remark = '' where name = '%s'" % self.doc.name)
		else:
			sql("update `tabStock Reconciliation` set remark = concat(remark, '%s'), modified = '%s' where name = '%s'" % (text + "<br>", nowdate(), self.doc.name))
		self.update_next_step(next_step)


	# --------------
	# validate item
	# --------------
	def validate_item(self, item, count, check_item = 1):
		det = sql("select item_code, has_serial_no from `tabItem` where name = '%s'"% cstr(item), as_dict = 1)
		if not det:
			text = "Item: " + cstr(item) + " mentioned at Row No. " + cstr(count) + "does not exist in the system"
			msgprint(text)
			self.add_remark(text, 'Validate Data', 0)
			check_item = 0
		elif det and det[0]['has_serial_no'] == 'Yes':
			text = "You cannot make Stock Reconciliation of items having serial no. You can directly upload serial no to update their inventory. Please remove Item Code : %s at Row No. %s" %(cstr(item), cstr(count))
			msgprint(text)
			self.add_remark(text, 'Validate Data', 0)
			check_item = 0
		return check_item


	# -------------------
	# validate warehouse
	# -------------------
	def validate_warehouse(self,wh,count, check_warehouse = 1):
		if not sql("select name from `tabWarehouse` where name = '%s'" % cstr(wh)):
			text = "Warehouse: " + cstr(wh) + " mentioned at Row No. " + cstr(count) + "does not exist in the system"
			self.add_remark(text,'Validate Data',0)
			check_warehouse = 0
		return check_warehouse


	# ---------------------------
	# validate data of .csv file
	# ---------------------------
	def validate_data(self,stock):
		self.add_remark('','Validate Data',1)

		# check whether file uploaded
		if not self.doc.file_list:
			set(self.doc,'next_step','Upload File and Save Document')
			msgprint("Please Attach File", raise_exception=1)

		# validate item and warehouse
		check_item,check_warehouse,count = 1, 1, 1
		for s in stock:
			count +=1
			check_item = self.validate_item(s[self.label['item_code']],count) or 0
			check_warehouse = self.validate_warehouse(s[self.label['warehouse']],count) or 0

		if check_item and check_warehouse:
			text = "Validation Completed Successfully..."
			self.add_remark(text,'Submit Document',0)
		return check_item and check_warehouse


	# ------------------------------
	# convert lines in .csv to list
	# ------------------------------
	def convert_into_list(self, stock, submit):
		count, st_list = 1, []
		for s in stock:
			if submit and len(s) != 4:
				msgprint("Data entered at Row No " + cstr(count) + " in Attachment File is not in correct format.", raise_exception=1)

			l = [s[0].encode("ascii"), s[1].encode("ascii"), s[2].encode("ascii"), s[3].encode("ascii")]
			st_list.append(l)
			count += 1
		return st_list

	# ------------------
	# get current stock
	# ------------------
	def get_current_stock(self, item_code, warehouse):
		bin = sql("select name from `tabBin` where item_code = '%s' and warehouse = '%s'" % (item_code, warehouse))
		prev_sle = bin and get_obj('Bin', bin[0][0]).get_prev_sle(self.doc.reconciliation_date,self.doc.reconciliation_time) or {}
		stock_uom = sql("select stock_uom from `tabItem` where name = %s",item_code)
		return {'actual_qty': prev_sle.get('bin_aqat', 0), 'stock_uom': stock_uom[0][0]}


	# -----------
	# update mar
	# -----------
	def update_mar(self, d, qty_diff):
		"""
			update item valuation in previous date and also on post date if no qty diff
		"""
		
		self.update_item_valuation_pre_date(d)
		
		if not flt(d[self.label['qty']]) and not flt(d[self.label['actual_qty']]):
			# seems like a special condition when there is no actual quanitity but there is a rate, may be only for setting a rate!
			self.make_sl_entry(1,d,1)
			self.make_sl_entry(1,d,-1)
		elif not qty_diff:
			self.update_item_valuation_post_date(d)
				
	# update valuation rate as csv file in all sle before reconciliation date
	# ------------------------------------------------------------------------
	def update_item_valuation_pre_date(self, d):
		mar = flt(d[self.label['mar']])		

		# previous sle
		prev_sle = sql("""
			select name, fcfs_stack
			from `tabStock Ledger Entry`
			where item_code = %s
			and warehouse = %s
			and ifnull(is_cancelled, 'No') = 'No'
			and timestamp(posting_date, posting_time) <= timestamp(%s, %s)
			""", (d[self.label['item_code']], d[self.label['warehouse']], self.doc.reconciliation_date, self.doc.reconciliation_time))

		for each in prev_sle:
			# updated fifo stack
			fstack = each[1] and [[i[0], mar] for i in eval(each[1])] or ''

			# update incoming rate, valuation rate, stock value and fifo stack
			sql("""update `tabStock Ledger Entry` 
			set incoming_rate = %s, valuation_rate = %s, stock_value = bin_aqat*%s, fcfs_stack = %s 
			where name = %s
			""", (mar, mar, mar, cstr(fstack), each[0]))
			
				
	# Update item valuation in all sle after the reconcliation date
	# ---------------------------------------------------------
	def update_item_valuation_post_date(self, d):
		bin = sql("select name from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d[self.label['item_code']], d[self.label['warehouse']]))
		bin_obj = get_obj('Bin', bin[0][0])

		# prev sle
		prev_sle = bin_obj.get_prev_sle(self.doc.reconciliation_date,self.doc.reconciliation_time)

		# update valuation in sle posted after reconciliation datetime
		bin_obj.update_item_valuation(posting_date = self.doc.reconciliation_date, posting_time = self.doc.reconciliation_time, prev_sle = prev_sle)

	# --------------
	# make sl entry
	# --------------
	def make_sl_entry(self, update_stock, stock, diff):
		values = []
		values.append({
				'item_code'					: stock[self.label['item_code']],
				'warehouse'					: stock[self.label['warehouse']],
				'transaction_date'	 		: now(),
				'posting_date'				: self.doc.reconciliation_date,
				'posting_time'			 	: self.doc.reconciliation_time,
				'voucher_type'			 	: self.doc.doctype,
				'voucher_no'				: self.doc.name,
				'voucher_detail_no'			: self.doc.name,
				'actual_qty'				: flt(update_stock) * flt(diff),
				'stock_uom'					: stock[self.label['stock_uom']],
				'incoming_rate'				: stock[self.label['mar']] or 0,
				'company'					: self.doc.company,
				'fiscal_year'				: self.doc.fiscal_year,
				'is_cancelled'			 	: (update_stock==1) and 'No' or 'Yes',
				'batch_no'					: '',
				'serial_no'					: ''
		 })
				
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(values)


	# -----------------------
	# get stock reco details
	# -----------------------
	def get_reconciliation_stock_details(self,submit = 0):
		import csv 
		stock = csv.reader(self.get_csv_file_data().splitlines())
		stock = self.convert_into_list(stock, submit)
		if stock[0][0] and stock[0][0].strip()=='Item Code':
			stock.pop(0)		# remove the labels
		check = self.validate_data(stock)
		if not check:
			return 0
		return stock

	# validate date and time
	# ------------------------
	def validate_datetime(self):
		if not self.doc.reconciliation_date:
			msgprint("Please Enter Reconciliation Date.", raise_exception=1)
		if not self.doc.reconciliation_time:
			msgprint("Please Enter Reconciliation Time.", raise_exception=1)



	# ----------------------
	# stock reconciliations
	# ----------------------
	def stock_reconciliations(self, submit = 0):
		self.validate_datetime()

		# get reco data
		rec_stock_detail = self.get_reconciliation_stock_details(submit) or []
		if not rec_stock_detail:
			msgprint("Please Check Remarks", raise_exception=1)

		count = 1
		for stock in rec_stock_detail:
			count += 1

			# Get qty as per system
			cur_stock_detail = self.get_current_stock(stock[self.label['item_code']],stock[self.label['warehouse']])
			stock.append(cur_stock_detail['stock_uom'])
			stock.append(cur_stock_detail['actual_qty'])

			# Qty Diff between file and system
			diff = flt(stock[self.label['qty']]) - flt(cur_stock_detail['actual_qty'])

			# Update MAR
			if not stock[self.label['mar']] == '~':
				self.update_mar(stock, diff)
			
			# Make sl entry if qty differ
			if diff:
				self.make_sl_entry(submit, stock, diff)

		if rec_stock_detail:
			text = "Stock Reconciliation Completed Successfully..."
			self.add_data_in_CSV(rec_stock_detail)
			self.add_remark(text,'Completed', 0)

	# Get csv data
	#--------------------------
	def get_csv_file_data(self):
		filename = self.doc.file_list.split(',')
		if not filename:
			msgprint("Please Attach File. ", raise_exception=1)
			
		from webnotes.utils import file_manager
		fn, content = file_manager.get_file(filename[1])
		
		if not type(content) == str:
			content = content.tostring()
		return content


	def getCSVelement(self,v):
		v = cstr(v)
		if not v: return ''
		if (',' in v) or ('' in v) or ('"' in	v):
			if '"' in v: v = v.replace('"', '""')
			return '"'+v+'"'
		else: return v or ''

	# Add qty diff column in attached file
	#----------------------------------------
	def add_data_in_CSV(self,data):
		filename = self.doc.file_list.split(',')
		head = []
		for h in ['Item Code','Warehouse','Qty','Actual','Difference','MAR']:
			head.append(self.getCSVelement(h))
		dset = (','.join(head) + "\n")
		for d in data:
			l = [d[self.label['item_code']],d[self.label['warehouse']],d[self.label['qty']],d[self.label['actual_qty']],flt(d[self.label['qty']])-flt(d[self.label['actual_qty']]),d[self.label['mar']]]
			s =[]
			for i in l:
				s.append(self.getCSVelement(i))
			dset +=(','.join(s)+"\n")
		
		from webnotes.utils import file_manager
		file_manager.write_file(filename[1], dset)

	# ----------
	# on submit
	# ----------
	def on_submit(self):
		self.stock_reconciliations(submit = 1)
