
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.utils import flt, getdate, add_days
from frappe.model.controller import DocListController
from datetime import date

class StockFreezeError(frappe.ValidationError): pass

class StockLedgerEntry(DocListController):

	def validate(self):
		from erpnext.stock.utils import validate_warehouse_company
		self.validate_mandatory()
		self.validate_item()
		validate_warehouse_company(self.warehouse, self.company)
		self.scrub_posting_time()
		
		from erpnext.accounts.utils import validate_fiscal_year
		validate_fiscal_year(self.posting_date, self.fiscal_year, 
			self.meta.get_label("posting_date"))

	def on_submit(self):
		self.check_stock_frozen_date()
		self.actual_amt_check()
		
		from erpnext.stock.doctype.serial_no.serial_no import process_serial_no
		process_serial_no(self)

	#check for item quantity available in stock
	def actual_amt_check(self):
		if self.batch_no:
			batch_bal_after_transaction = flt(frappe.db.sql("""select sum(actual_qty)
				from `tabStock Ledger Entry`
				where warehouse=%s and item_code=%s and batch_no=%s""",
				(self.warehouse, self.item_code, self.batch_no))[0][0])

			if batch_bal_after_transaction < 0:
				self.update({
					'batch_bal': batch_bal_after_transaction - self.actual_qty
				})

				frappe.throw("""Not enough quantity (requested: %(actual_qty)s, \
					current: %(batch_bal)s in Batch <b>%(batch_no)s</b> for Item \
					<b>%(item_code)s</b> at Warehouse <b>%(warehouse)s</b> \
					as on %(posting_date)s %(posting_time)s""" % self.as_dict())

				self.pop('batch_bal')

	def validate_mandatory(self):
		mandatory = ['warehouse','posting_date','voucher_type','voucher_no','actual_qty','company']
		for k in mandatory:
			if not self.get(k):
				msgprint("Stock Ledger Entry: '%s' is mandatory" % k, raise_exception = 1)
			elif k == 'warehouse':
				if not frappe.db.exists("Warehouse", self.get(k)):
					msgprint("Warehouse: '%s' does not exist in the system. Please check." % 
						self.get(k), raise_exception = 1)

	def validate_item(self):
		item_det = frappe.db.sql("""select name, has_batch_no, docstatus,
			is_stock_item, has_serial_no, serial_no_series
			from tabItem where name=%s""",
			self.item_code, as_dict=True)[0]

		if item_det.is_stock_item != 'Yes':
			frappe.throw("""Item: "%s" is not a Stock Item.""" % self.item_code)

		# check if batch number is required
		if item_det.has_batch_no =='Yes' and self.voucher_type != 'Stock Reconciliation':
			if not self.batch_no:
				frappe.throw("Batch number is mandatory for Item '%s'" % self.item_code)

			# check if batch belongs to item
			if not frappe.db.get_value("Batch", 
					{"item": self.item_code, "name": self.batch_no}):
				frappe.throw("'%s' is not a valid Batch Number for Item '%s'" % 
					(self.batch_no, self.item_code))

		if not self.stock_uom:
			self.stock_uom = item_det.stock_uom

	def check_stock_frozen_date(self):
		stock_frozen_upto = frappe.db.get_value('Stock Settings', None, 'stock_frozen_upto') or ''
		if stock_frozen_upto:
			stock_auth_role = frappe.db.get_value('Stock Settings', None,'stock_auth_role')
			if getdate(self.posting_date) <= getdate(stock_frozen_upto) and not stock_auth_role in frappe.user.get_roles():
				msgprint("You are not authorized to do / modify back dated stock entries before %s" % getdate(stock_frozen_upto).strftime('%d-%m-%Y'), raise_exception=StockFreezeError)

		stock_frozen_upto_days = int(frappe.db.get_value('Stock Settings', None, 'stock_frozen_upto_days') or 0)
		if stock_frozen_upto_days:
			stock_auth_role = frappe.db.get_value('Stock Settings', None,'stock_auth_role')
			older_than_x_days_ago = (add_days(getdate(self.posting_date), stock_frozen_upto_days) <= date.today())
			if older_than_x_days_ago and not stock_auth_role in frappe.user.get_roles():
				msgprint("You are not authorized to do / modify back dated stock entries older than %d days ago" %stock_frozen_upto_days, raise_exception=StockFreezeError)


	def scrub_posting_time(self):
		if not self.posting_time or self.posting_time == '00:0':
			self.posting_time = '00:00'

def on_doctype_update():
	if not frappe.db.sql("""show index from `tabStock Ledger Entry`
		where Key_name="posting_sort_index" """):
		frappe.db.commit()
		frappe.db.sql("""alter table `tabStock Ledger Entry`
			add index posting_sort_index(posting_date, posting_time, name)""")