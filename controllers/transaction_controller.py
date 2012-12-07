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
import webnotes.model
from webnotes import _, _dict
from webnotes.utils import cint
import json

from webnotes.model.controller import DocListController

class TransactionController(DocListController):
	def __init__(self, doc, doclist):
		super(TransactionController, self).__init__(doc, doclist)
		self.cur_docstatus = cint(webnotes.conn.get_value(self.doc.doctype, 
			self.doc.name, "docstatus"))
		
	@property
	def precision(self):
		if not hasattr(self, "_precision"):
			self._precision = _dict()
			self._precision.main = self.meta.get_precision_map()
			self._precision.item = self.meta.get_precision_map(parentfield = \
				self.item_table_field)
			if self.meta.get_field(self.fmap.taxes_and_charges):
				self._precision.tax = self.meta.get_precision_map(parentfield = \
					self.fmap.taxes_and_charges)
		return self._precision
		
	@property
	def item_doclist(self):
		if not hasattr(self, "_item_doclist"):
			self._item_doclist = self.doclist.get({"parentfield": self.item_table_field})
		return self._item_doclist

	@property
	def tax_doclist(self):
		if not hasattr(self, "_tax_doclist"):
			self._tax_doclist = self.doclist.get(
				{"parentfield": self.fmap.taxes_and_charges})
		return self._tax_doclist
	
	@property
	def stock_items(self):
		if not hasattr(self, "_stock_items"):
			item_codes = list(set(item.item_code for item in self.item_doclist))
			self._stock_items = [r[0] for r in webnotes.conn.sql("""select name
				from `tabItem` where name in (%s) and is_stock_item='Yes'""" % \
				(", ".join((["%s"]*len(item_codes))),), item_codes)]

		return self._stock_items
	
	@property
	def fmap(self):
		if not hasattr(self, "_fmap"):
			if self.doc.doctype in ["Lead", "Quotation", "Sales Order", "Sales Invoice",
					"Delivery Note"]:
				self._fmap = webnotes._dict(	{
					"exchange_rate": "conversion_rate",
					"taxes_and_charges": "other_charges",
					"taxes_and_charges_master": "charge",
					"taxes_and_charges_total": "other_charges_total",
					"net_total_print": "net_total_print",
					"grand_total_print": "grand_total_export",
					"grand_total_in_words": "grand_total_in_words",
					"grand_total_in_words_print": "grand_total_in_words_print",
					"rounded_total_print": "rounded_total_export",
					"rounded_total_in_words": "in_words",
					"rounded_total_in_words_print": "in_words_export",
					"print_ref_rate": "ref_rate",
					"discount": "adj_rate",
					"print_rate": "export_rate",
					"print_amount": "export_amount",
					"ref_rate": "base_ref_rate",
					"rate": "basic_rate",
					
					"plc_exchange_rate": "plc_conversion_rate",
					"tax_calculation": "other_charges_calculation",
					"cost_center": "cost_center_other_charges",
				})
			else:
				self._fmap = webnotes._dict({
					"exchange_rate": "conversion_rate",
					"taxes_and_charges": "purchase_tax_details",
					"taxes_and_charges_master": "purchase_other_charges",
					"taxes_and_charges_total": "total_tax",
					"net_total_print": "net_total_import",
					"grand_total_print": "grand_total_import",
					"grand_total_in_words": "in_words",
					"grand_total_in_words_print": "in_words_import",
					"rounded_total_print": "rounded_total_print",
					"rounded_total_in_words": "rounded_total_in_words",
					"rounded_total_in_words_print": "rounded_total_in_words_print",
					"print_ref_rate": "import_ref_rate",
					"discount": "discount_rate",
					"print_rate": "import_rate",
					"print_amount": "import_amount",
					"ref_rate": "purchase_ref_rate",
					"rate": "purchase_rate",
					
					"valuation_tax_amount": "item_tax_amount"
				})
				
				if self.doc.doctype == "Purchase Invoice":
					self._fmap.update({
						"rate": "rate"
					})
			
		return self._fmap or webnotes._dict()