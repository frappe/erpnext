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

from buying.utils import get_item_details

from utilities.transaction_base import TransactionBase
class BuyingController(TransactionBase):
	def validate(self):
		pass
		
	def update_item_details(self):
		for item in self.doclist.get({"parentfield": self.fname}):
			ret = get_item_details({
				"doctype": self.doc.doctype,
				"docname": self.doc.name,
				"item_code": item.item_code,
				"warehouse": item.warehouse,
				"supplier": self.doc.supplier,
				"transaction_date": self.doc.posting_date,
				"conversion_rate": self.doc.conversion_rate
			})
			for r in ret:
				if not item.fields.get(r):
					item.fields[r] = ret[r]
