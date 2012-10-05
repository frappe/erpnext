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

from webnotes.model.doc import Document
from webnotes import msgprint


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		self.cl = []
	
	# validate currency
	def is_currency_valid(self, currency):
		if currency in self.cl:
			return 1
			
		if webnotes.conn.sql("select name from tabCurrency where name=%s", currency):
			self.cl.append(currency)
			return 1
		else:
			return 0
			
	def download_template(self, arg=None):
		"""download 3 column template with all Items"""
		default_currency = webnotes.conn.get_default('currency')
		item_list = webnotes.conn.sql("""select name from tabItem where 
			(ifnull(is_sales_item,'')='Yes' or ifnull(is_service_item,'')='Yes')""")
		data = [self.get_price(i[0], default_currency) for i in item_list]
		return [['Item', 'Rate', 'Currency']] + data
	
	def get_price(self, item, default_currency):
		rate = webnotes.conn.sql("""select ref_rate, ref_currency from `tabItem Price` 
			where parent=%s and price_list_name=%s""", (item, self.doc.name))
		return [item, rate and rate[0][0] or 0, rate and rate[0][1] or default_currency]
	
	# update prices in Price List
	def update_prices(self):
		from webnotes.utils.datautils import read_csv_content_from_attached_file
		data = read_csv_content_from_attached_file(self.doc)
		
		webnotes.conn.auto_commit_on_many_writes = 1
				
		updated = 0
		
		for line in data:
			if line and len(line)==3 and line[0]!='Item':
				# if item exists
				if webnotes.conn.sql("select name from tabItem where name=%s", line[0]):
					if self.is_currency_valid(line[2]):
						# if price exists
						ref_ret_detail = webnotes.conn.sql("select name from `tabItem Price` where parent=%s and price_list_name=%s and ref_currency=%s", \
							(line[0], self.doc.name, line[2]))
						if ref_ret_detail:
							webnotes.conn.sql("update `tabItem Price` set ref_rate=%s where name=%s", (line[1], ref_ret_detail[0][0]))
						else:
							d = Document('Item Price')
							d.parent = line[0]
							d.parentfield = 'ref_rate_details'
							d.parenttype = 'Item'
							d.price_list_name = self.doc.name
							d.ref_rate = line[1]
							d.ref_currency = line[2]
							d.save(1)
						updated += 1
					else:
						msgprint("[Ignored] Unknown currency '%s' for Item '%s'" % (line[2], line[0]))
				else:
					msgprint("[Ignored] Did not find Item '%s'" % line[1])
		
		msgprint("<b>%s</b> items updated" % updated)
		webnotes.conn.auto_commit_on_many_writes = 0