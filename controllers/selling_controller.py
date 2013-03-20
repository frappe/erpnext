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
