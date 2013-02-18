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
from webnotes.model.code import get_obj
from setup.utils import get_company_currency

from controllers.buying_controller import BuyingController
class DocType(BuyingController):
	def __init__(self, doc, doclist=None):
		self.doc, self.doclist = doc, doclist or []
		self.tname, self.fname = "Supplier Quotation Item", "quotation_items"
		
	def validate(self):
		super(DocType, self).validate()
		
		if not self.doc.status:
			self.doc.status = "Draft"

		import utilities
		utilities.validate_status(self.doc.status, ["Draft", "Submitted", "Stopped", 
			"Cancelled"])
		
		self.validate_fiscal_year()
		self.validate_common()

	def on_submit(self):
		purchase_controller = webnotes.get_obj("Purchase Common")
		purchase_controller.is_item_table_empty(self)
		
		webnotes.conn.set(self.doc, "status", "Submitted")

	def on_cancel(self):
		webnotes.conn.set(self.doc, "status", "Cancelled")
		
	def on_trash(self):
		pass
		
	def get_indent_details(self):
		if self.doc.indent_no:
			mapper = get_obj("DocType Mapper", "Material Request-Supplier Quotation")
			mapper.dt_map("Material Request", "Supplier Quotation", self.doc.indent_no,
				self.doc, self.doclist, """[['Material Request', 'Supplier Quotation'],
				['Material Request Item', 'Supplier Quotation Item']]""")
			
			from webnotes.model.bean import getlist
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
		pc.validate_for_items(self)
		pc.get_prevdoc_date(self)
		pc.validate_reference_value(self)
