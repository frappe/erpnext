# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

class ItemPriceDuplicateItem(Exception): pass

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def on_update(self):
		self.update_price_list_details()
		self.update_item_details()
		self.check_duplicate_item()

	def update_price_list_details(self):
		self.doc.buying_or_selling = webnotes.conn.get_value("Price List", self.doc.price_list, 
			"buying_or_selling")

		self.doc.currency = webnotes.conn.get_value("Price List", self.doc.price_list, 
			"currency")

	def update_item_details(self):
		self.doc.item_name = webnotes.conn.get_value("Item", self.doc.item_code, "item_name")

		self.doc.item_description = webnotes.conn.get_value("Item", self.doc.item_code, 
			"description")

	def check_duplicate_item(self):
		for item_code, price_list in webnotes.conn.sql("""select item_code, price_list 
			from `tabItem Price`"""):

				if item_code == self.doc.item_code and price_list == self.doc.price_list:
					webnotes.throw(_("Duplicate Item: ") + self.doc.item_code + 
						_(" already available in Price List: ") + self.doc.price_list, 
						ItemPriceDuplicateItem)