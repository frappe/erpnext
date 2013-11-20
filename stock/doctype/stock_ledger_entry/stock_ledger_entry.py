# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint
from webnotes.utils import flt, getdate
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate(self):
		from stock.utils import validate_warehouse_user, validate_warehouse_company
		self.validate_mandatory()
		self.validate_item()
		validate_warehouse_user(self.doc.warehouse)
		validate_warehouse_company(self.doc.warehouse, self.doc.company)
		self.scrub_posting_time()
		
		from accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.doc.posting_date, self.doc.fiscal_year, self.meta.get_label("posting_date"))
		
	def on_submit(self):
		self.check_stock_frozen_date()
		self.actual_amt_check()
		
		from stock.doctype.serial_no.serial_no import process_serial_no
		process_serial_no(self.doc)
		
	#check for item quantity available in stock
	def actual_amt_check(self):
		if self.doc.batch_no:
			batch_bal_after_transaction = flt(webnotes.conn.sql("""select sum(actual_qty) 
				from `tabStock Ledger Entry` 
				where warehouse=%s and item_code=%s and batch_no=%s""", 
				(self.doc.warehouse, self.doc.item_code, self.doc.batch_no))[0][0])
			
			if batch_bal_after_transaction < 0:
				self.doc.fields.update({
					'batch_bal': batch_bal_after_transaction - self.doc.actual_qty
				})
				
				webnotes.throw("""Not enough quantity (requested: %(actual_qty)s, \
					current: %(batch_bal)s in Batch <b>%(batch_no)s</b> for Item \
					<b>%(item_code)s</b> at Warehouse <b>%(warehouse)s</b> \
					as on %(posting_date)s %(posting_time)s""" % self.doc.fields)

				self.doc.fields.pop('batch_bal')

	def validate_mandatory(self):
		mandatory = ['warehouse','posting_date','voucher_type','voucher_no','actual_qty','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				msgprint("Stock Ledger Entry: '%s' is mandatory" % k, raise_exception = 1)
			elif k == 'warehouse':
				if not webnotes.conn.sql("select name from tabWarehouse where name = '%s'" % self.doc.fields.get(k)):
					msgprint("Warehouse: '%s' does not exist in the system. Please check." % self.doc.fields.get(k), raise_exception = 1)

	def validate_item(self):
		item_det = webnotes.conn.sql("""select name, has_batch_no, docstatus, 
			is_stock_item, has_serial_no, serial_no_series 
			from tabItem where name=%s""", 
			self.doc.item_code, as_dict=True)[0]

		if item_det.is_stock_item != 'Yes':
			webnotes.throw("""Item: "%s" is not a Stock Item.""" % self.doc.item_code)
			
		# check if batch number is required
		if item_det.has_batch_no =='Yes' and self.doc.voucher_type != 'Stock Reconciliation':
			if not self.doc.batch_no:
				webnotes.throw("Batch number is mandatory for Item '%s'" % self.doc.item_code)
		
			# check if batch belongs to item
			if not webnotes.conn.sql("""select name from `tabBatch` 
				where item='%s' and name ='%s' and docstatus != 2""" % (self.doc.item_code, self.doc.batch_no)):
				webnotes.throw("'%s' is not a valid Batch Number for Item '%s'" % (self.doc.batch_no, self.doc.item_code))
				
		if not self.doc.stock_uom:
			self.doc.stock_uom = item_det.stock_uom
					
	def check_stock_frozen_date(self):
		stock_frozen_upto = webnotes.conn.get_value('Stock Settings', None, 'stock_frozen_upto') or ''
		if stock_frozen_upto:
			stock_auth_role = webnotes.conn.get_value('Stock Settings', None,'stock_auth_role')
			if getdate(self.doc.posting_date) <= getdate(stock_frozen_upto) and not stock_auth_role in webnotes.user.get_roles():
				msgprint("You are not authorized to do / modify back dated stock entries before %s" % getdate(stock_frozen_upto).strftime('%d-%m-%Y'), raise_exception=1)

	def scrub_posting_time(self):
		if not self.doc.posting_time or self.doc.posting_time == '00:0':
			self.doc.posting_time = '00:00'

def on_doctype_update():
	if not webnotes.conn.sql("""show index from `tabStock Ledger Entry` 
		where Key_name="posting_sort_index" """):
		webnotes.conn.commit()
		webnotes.conn.sql("""alter table `tabStock Ledger Entry` 
			add index posting_sort_index(posting_date, posting_time, name)""")