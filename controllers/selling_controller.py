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
from setup.utils import get_company_currency
from webnotes import msgprint, _

from controllers.stock_controller import StockController

class SellingController(StockController):
	def validate(self):
		super(SellingController, self).validate()
		self.set_total_in_words()
		
	def set_total_in_words(self):
		from webnotes.utils import money_in_words
		company_currency = get_company_currency(self.doc.company)
		
		disable_rounded_total = cint(webnotes.conn.get_value("Global Defaults", None, 
			"disable_rounded_total"))
			
		if self.meta.get_field("in_words"):
			self.doc.in_words = money_in_words(disable_rounded_total and 
				self.doc.grand_total or self.doc.rounded_total, company_currency)
		if self.meta.get_field("in_words_export"):
			self.doc.in_words_export = money_in_words(disable_rounded_total and 
				self.doc.grand_total_export or self.doc.rounded_total_export, self.doc.currency)

	def set_buying_amount(self, stock_ledger_entries = None):
		from stock.utils import get_buying_amount
		if not stock_ledger_entries:
			stock_ledger_entries = self.get_stock_ledger_entries()

		item_sales_bom = {}
		for d in self.doclist.get({"parentfield": "packing_details"}):
			new_d = webnotes._dict(d.fields.copy())
			new_d.total_qty = -1 * d.qty
			item_sales_bom.setdefault(d.parent_item, []).append(new_d)
		
		if stock_ledger_entries:
			for item in self.doclist.get({"parentfield": self.fname}):
				if item.item_code in self.stock_items or \
						(item_sales_bom and item_sales_bom.get(item.item_code)):
					buying_amount = get_buying_amount(item.item_code, item.warehouse, -1*item.qty, 
						self.doc.doctype, self.doc.name, item.name, stock_ledger_entries, 
						item_sales_bom)
					
					item.buying_amount = buying_amount >= 0.01 and buying_amount or 0
					webnotes.conn.set_value(item.doctype, item.name, "buying_amount", 
						item.buying_amount)
						
	def check_expense_account(self, item):
		if item.buying_amount and not item.expense_account:
			msgprint(_("""Expense account is mandatory for item: """) + item.item_code, 
				raise_exception=1)
				
		if item.buying_amount and not item.cost_center:
			msgprint(_("""Cost Center is mandatory for item: """) + item.item_code, 
				raise_exception=1)