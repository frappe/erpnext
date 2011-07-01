# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, flt, cstr, getdate, nowdate
import datetime

sql = webnotes.conn.sql
msgprint = webnotes.msgprint
	
# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist


# ********************************* validate warranty / amc status ***************************************

	# --------------------
	# validate amc status
	# --------------------
	def validate_amc_status(self):
		if self.doc.amc_expiry_date and getdate(self.doc.amc_expiry_date) >= datetime.date.today() and self.doc.maintenance_status == 'Out of AMC':
			msgprint("AMC expiry date and maintenance status mismatch. Please verify")
			raise Exception
		elif (not self.doc.amc_expiry_date or getdate(self.doc.amc_expiry_date) < datetime.date.today()) and self.doc.maintenance_status == 'Under AMC':
			msgprint("AMC expiry date and maintenance status mismatch. Please verify")
			raise Exception


	# -------------------------
	# validate warranty status
	# -------------------------
	def validate_warranty_status(self):
		if self.doc.warranty_expiry_date and getdate(self.doc.warranty_expiry_date) >= datetime.date.today() and self.doc.maintenance_status == 'Out of Warranty':
			msgprint("Warranty expiry date and maintenance status mismatch. Please verify")
			raise Exception
		elif (not self.doc.warranty_expiry_date or getdate(self.doc.warranty_expiry_date) < datetime.date.today()) and self.doc.maintenance_status == 'Under Warranty':
			msgprint("Warranty expiry date and maintenance status mismatch. Please verify")
			raise Exception


	# -------------------------------
	# validate warranty / amc status
	# -------------------------------
	def validate_warranty_amc_status(self):
		self.validate_warranty_status()
		self.validate_amc_status()


	def validate_warehouse(self):
		if self.doc.status=='In Store' and not self.doc.warehouse:
			msgprint("Warehouse is mandatory if this Serial No is <b>In Store</b>", raise_exception=1)

	def validate_item(self):
		item = sql("select name, has_serial_no from tabItem where name = '%s'" % self.doc.item_code)
		if not item:
			msgprint("Item is not exists in the system", raise_exception=1)
		elif item[0][1] == 'No':
			msgprint("To proceed please select 'Yes' in 'Has Serial No' in Item master: '%s'" % self.doc.item_code, raise_exception=1)
			

	# ---------
	# validate
	# ---------
	def validate(self):
		self.validate_warranty_amc_status()
		self.validate_warehouse()
		self.validate_item()


	# ------------------------
	# make stock ledger entry
	# ------------------------
	def make_stock_ledger_entry(self, update_stock):
		from webnotes.model.code import get_obj
		values = [{
			'item_code'				: self.doc.item_code,
			'warehouse'				: self.doc.warehouse,
			'transaction_date'		: nowdate(),
			'posting_date'			: self.doc.purchase_date or (self.doc.creation and self.doc.creation.split(' ')[0]) or nowdate(),
			'posting_time'			: self.doc.purchase_time or '00:00',
			'voucher_type'			: 'Serial No',
			'voucher_no'			: self.doc.name,
			'voucher_detail_no'	 	: '', 
			'actual_qty'			: 1, 
			'stock_uom'				: webnotes.conn.get_value('Item', self.doc.item_code, 'stock_uom'),
			'incoming_rate'			: self.doc.purchase_rate,
			'company'				: self.doc.company,
			'fiscal_year'			: self.doc.fiscal_year,
			'is_cancelled'			: update_stock and 'No' or 'Yes',
			'batch_no'				: '',
			'serial_no'				: self.doc.name
		}]
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(values)


	# ----------
	# on update
	# ----------
	def on_update(self):
		if self.doc.warehouse and not sql("select name from `tabStock Ledger Entry` where serial_no = '%s'" % (self.doc.name)) and self.doc.status == 'In Store':
			self.make_stock_ledger_entry(update_stock = 1)


	# ---------
	# on trash
	# ---------
	def on_trash(self):
		if self.doc.status == 'Delivered':
			msgprint("Cannot trash Serial No : %s as it is already Delivered" % (self.doc.name), raise_exception = 1)
		else:
			webnotes.conn.set(self.doc, 'status', 'Not in Use')
			self.make_stock_ledger_entry(update_stock = 0)


	def on_cancel(self):
		self.on_trash()

	# -----------
	# on restore
	# -----------
	def on_restore(self):
		self.make_stock_ledger_entry(update_stock = 1)
