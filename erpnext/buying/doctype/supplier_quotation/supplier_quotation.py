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

import webnotes
from webnotes.model.code import get_obj
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=None):
		self.doc, self.doclist = doc, doclist or []
		self.tname, self.fname = "Supplier Quotation Item", "quotation_items"

	def autoname(self):
		"""autoname based on naming series value"""
		from webnotes.model.doc import make_autoname
		self.doc.name = make_autoname(self.doc.naming_series + ".#####")
		
	def validate(self):
		self.validate_fiscal_year()
		self.validate_common()
		self.set_in_words()
		self.doc.status = "Draft"

	def on_submit(self):
		webnotes.conn.set(self.doc, "status", "Submitted")

	def on_cancel(self):
		webnotes.conn.set(self.doc, "status", "Cancelled")
		
	def on_trash(self):
		pass
		
	def get_item_details(self, args=None):
		if args:
			return get_obj(dt='Purchase Common').get_item_details(self, args)
		else:
			obj = get_obj('Purchase Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					temp = {
						'item_code': doc.fields.get('item_code'),
						'warehouse': doc.fields.get('warehouse')
					}
					ret = obj.get_item_details(self, json.dumps(temp))
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]

	def get_indent_details(self):
		if self.doc.indent_no:
			mapper = get_obj("DocType Mapper", "Purchase Request-Supplier Quotation")
			mapper.dt_map("Purchase Request", "Supplier Quotation", self.doc.indent_no,
				self.doc, self.doclist, """[['Purchase Request', 'Supplier Quotation'],
				['Purchase Request Item', 'Supplier Quotation Item']]""")
			
			from webnotes.model.doclist import getlist
			for d in getlist(self.doclist, self.fname):
				if d.item_code and not d.purchase_rate:
					d.purchase_ref_rate = d.discount_rate = d.purchase_rate = 0.0
					d.import_ref_rate = d.import_rate = 0.0
	
	def load_default_taxes(self):
		self.doclist = get_obj('Purchase Common').load_default_taxes(self)
	
	def get_purchase_tax_details(self):
		self.doclist = get_obj('Purchase Common').get_purchase_tax_details(self)

	def validate_fiscal_year(self):
		get_obj(dt = 'Purchase Common').validate_fiscal_year( \
			self.doc.fiscal_year, self.doc.transaction_date, 'Quotation Date')
			
	def validate_common(self):
		pc = get_obj('Purchase Common')
		pc.validate_mandatory(self)
		pc.validate_for_items(self)
		pc.validate_conversion_rate(self)
		pc.get_prevdoc_date(self)
		pc.validate_reference_value(self)
		
	def set_in_words(self):
		pc = get_obj('Purchase Common')
		company_currency = TransactionBase().get_company_currency(self.doc.company)
		self.doc.in_words = pc.get_total_in_words(company_currency, self.doc.grand_total)
		self.doc.in_words_import = pc.get_total_in_words(self.doc.currency, self.doc.grand_total_import)
