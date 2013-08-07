# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, flt, cstr
from webnotes import msgprint, _
import webnotes.defaults

from controllers.accounts_controller import AccountsController

class StockController(AccountsController):
	def get_gl_entries_for_stock(self, against_stock_account, amount, warehouse=None, 
			stock_in_hand_account=None, cost_center=None):
		if not stock_in_hand_account and warehouse:
			stock_in_hand_account = webnotes.conn.get_value("Warehouse", warehouse, "account")
		
		if amount:
			gl_entries = [
				# stock in hand account
				self.get_gl_dict({
					"account": stock_in_hand_account,
					"against": against_stock_account,
					"debit": amount,
					"remarks": self.doc.remarks or "Accounting Entry for Stock",
				}, self.doc.docstatus == 2),
				
				# account against stock in hand
				self.get_gl_dict({
					"account": against_stock_account,
					"against": stock_in_hand_account,
					"credit": amount,
					"cost_center": cost_center or None,
					"remarks": self.doc.remarks or "Accounting Entry for Stock",
				}, self.doc.docstatus == 2),
			]
			
			return gl_entries
			
	def sync_stock_account_balance(self, warehouse_list, cost_center=None, posting_date=None):
		from accounts.utils import get_stock_and_account_difference
		acc_diff = get_stock_and_account_difference(warehouse_list)
		if not cost_center:
			cost_center = self.get_company_default("cost_center")
		gl_entries = []
		for account, diff in acc_diff.items():
			if diff:
				stock_adjustment_account = self.get_company_default("stock_adjustment_account")
				gl_entries += self.get_gl_entries_for_stock(stock_adjustment_account, diff, 
					stock_in_hand_account=account, cost_center=cost_center)
					
		if gl_entries:
			from accounts.general_ledger import make_gl_entries

			if posting_date:
				for entries in gl_entries:
					entries["posting_date"] = posting_date

			make_gl_entries(gl_entries)
				
	def get_sl_entries(self, d, args):		
		sl_dict = {
			"item_code": d.item_code,
			"warehouse": d.warehouse,
			"posting_date": self.doc.posting_date,
			"posting_time": self.doc.posting_time,
			"voucher_type": self.doc.doctype,
			"voucher_no": self.doc.name,
			"voucher_detail_no": d.name,
			"actual_qty": (self.doc.docstatus==1 and 1 or -1)*flt(d.stock_qty),
			"stock_uom": d.stock_uom,
			"incoming_rate": 0,
			"company": self.doc.company,
			"fiscal_year": self.doc.fiscal_year,
			"is_cancelled": self.doc.docstatus==2 and "Yes" or "No",
			"batch_no": cstr(d.batch_no).strip(),
			"serial_no": d.serial_no,
			"project": d.project_name
		}
		
		sl_dict.update(args)
		return sl_dict
		
	def make_sl_entries(self, sl_entries, is_amended=None):
		if sl_entries:
			from webnotes.model.code import get_obj
			get_obj('Stock Ledger').update_stock(sl_entries, is_amended)
		
	def get_stock_ledger_entries(self, item_list=None, warehouse_list=None):
		if not (item_list and warehouse_list):
			item_list, warehouse_list = self.get_distinct_item_warehouse()
			
		if item_list and warehouse_list:
			return webnotes.conn.sql("""select item_code, voucher_type, voucher_no,
				voucher_detail_no, posting_date, posting_time, stock_value,
				warehouse, actual_qty as qty from `tabStock Ledger Entry` 
				where ifnull(`is_cancelled`, "No") = "No" and company = %s 
				and item_code in (%s) and warehouse in (%s)
				order by item_code desc, warehouse desc, posting_date desc, 
				posting_time desc, name desc""" % 
				('%s', ', '.join(['%s']*len(item_list)), ', '.join(['%s']*len(warehouse_list))), 
				tuple([self.doc.company] + item_list + warehouse_list), as_dict=1)

	def get_distinct_item_warehouse(self):
		item_list = []
		warehouse_list = []
		for item in self.doclist.get({"parentfield": self.fname}) \
				+ self.doclist.get({"parentfield": "packing_details"}):
			item_list.append(item.item_code)
			warehouse_list.append(item.warehouse)
			
		return list(set(item_list)), list(set(warehouse_list))
		
	def make_cancel_gl_entries(self):
		if webnotes.conn.sql("""select name from `tabGL Entry` where voucher_type=%s 
			and voucher_no=%s and ifnull(is_cancelled, 'No')='No'""",
			(self.doc.doctype, self.doc.name)):
				self.make_gl_entries()