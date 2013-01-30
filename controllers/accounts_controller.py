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

from utilities.transaction_base import TransactionBase

class AccountsController(TransactionBase):
	def get_gl_dict(self, args, cancel):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = {
			'company': self.doc.company, 
			'posting_date': self.doc.posting_date,
			'voucher_type': self.doc.doctype,
			'voucher_no': self.doc.name,
			'aging_date': self.doc.fields.get("aging_date") or self.doc.posting_date,
			'remarks': self.doc.remarks,
			'is_cancelled': cancel and "Yes" or "No",
			'fiscal_year': self.doc.fiscal_year,
			'debit': 0,
			'credit': 0,
			'is_opening': self.doc.fields.get("is_opening") or "No",
		}
		gl_dict.update(args)
		return gl_dict
	
	def get_company_abbr(self):
		return webnotes.conn.get_value("Company", self.doc.company, "abbr")
		
	def get_stock_in_hand_account(self):
		stock_in_hand = webnotes.conn.get_value("Company", self.doc.company, "stock_in_hand")
		
		if not stock_in_hand:
			webnotes.msgprint("""Please specify "Stock In Hand" account 
				for company: %s""" % (self.doc.company,), raise_exception=1)
				
		return stock_in_hand
