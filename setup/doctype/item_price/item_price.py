# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def on_update(self):
		self.update_price_list_details()
		self.update_item_details()

	def update_price_list_details(self):
		self.doc.buying_or_selling = webnotes.conn.get_value("Price List", self.doc.price_list, 
			"buying_or_selling")

		self.doc.currency = webnotes.conn.get_value("Price List", self.doc.price_list, 
			"currency")

	def update_item_details(self):
		self.doc.item_name = webnotes.conn.get_value("Item", self.doc.item_code, "item_name")

		self.doc.item_description = webnotes.conn.get_value("Item", self.doc.item_code, 
			"description")