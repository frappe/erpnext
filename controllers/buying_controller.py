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
from webnotes import _, msgprint
from webnotes.utils import flt

from buying.utils import get_item_details
from setup.utils import get_company_currency

from controllers.accounts_controller import AccountsController

class BuyingController(AccountsController):
	def validate(self):		
		if self.meta.get_field("currency"):
			self.company_currency = get_company_currency(self.doc.company)
			self.validate_conversion_rate("currency", "conversion_rate")
			
			if self.doc.price_list_name and self.doc.price_list_currency:
				self.validate_conversion_rate("price_list_currency", "plc_conversion_rate")
				
			# set total in words
			self.set_total_in_words()
		
	def update_item_details(self):
		for item in self.doclist.get({"parentfield": self.fname}):
			ret = get_item_details({
				"doctype": self.doc.doctype,
				"docname": self.doc.name,
				"item_code": item.item_code,
				"warehouse": item.warehouse,
				"supplier": self.doc.supplier,
				"transaction_date": self.doc.posting_date,
				"conversion_rate": self.doc.conversion_rate,
				"price_list_name": self.doc.price_list_name,
				"price_list_currency": self.doc.price_list_currency,
				"plc_conversion_rate": self.doc.plc_conversion_rate
			})
			for r in ret:
				if not item.fields.get(r):
					item.fields[r] = ret[r]
	
	def validate_conversion_rate(self, currency_field, conversion_rate_field):
		"""common validation for currency and price list currency"""
		
		currency = self.doc.fields.get(currency_field)
		conversion_rate = flt(self.doc.fields.get(conversion_rate_field))
		conversion_rate_label = self.meta.get_label(conversion_rate_field)
		
		if conversion_rate == 0:
			msgprint(conversion_rate_label + _(' cannot be 0'), raise_exception=True)
		
		# parenthesis for 'OR' are necessary as we want it to evaluate as 
		# mandatory valid condition and (1st optional valid condition 
		# 	or 2nd optional valid condition)
		valid_conversion_rate = (conversion_rate and 
			((currency == self.company_currency and conversion_rate == 1.00)
				or (currency != self.company_currency and conversion_rate != 1.00)))

		if not valid_conversion_rate:
			msgprint(_('Please enter valid ') + conversion_rate_label + (': ') 
				+ ("1 %s = [?] %s" % (currency, self.company_currency)),
				raise_exception=True)

	def set_total_in_words(self):
		from webnotes.utils import money_in_words
		company_currency = get_company_currency(self.doc.company)
		if self.meta.get_field("in_words"):
			self.doc.in_words = money_in_words(self.doc.grand_total, company_currency)
		if self.meta.get_field("in_words_import"):
			self.doc.in_words_import = money_in_words(self.doc.grand_total_import,
		 		self.doc.currency)
		
	def calculate_taxes_and_totals(self):
		pass