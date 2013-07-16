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

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint
import webnotes.defaults
from controllers.accounts_controller import AccountsController

class StockController(AccountsController):
	def get_gl_entries_for_stock(self, against_stock_account, amount, 
			stock_in_hand_account=None, cost_center=None):
		if not stock_in_hand_account:
			stock_in_hand_account = self.get_company_default("stock_in_hand_account")
		if not cost_center:
			cost_center = self.get_company_default("stock_adjustment_cost_center")
		
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