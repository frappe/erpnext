# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		self.make_adjustment_jv_for_auto_inventory()
		
	def make_adjustment_jv_for_auto_inventory(self):
		previous_auto_inventory_accounting = cint(webnotes.conn.get_value("Accounts Settings", 
			None, "auto_inventory_accounting"))
		if cint(self.doc.auto_inventory_accounting) != previous_auto_inventory_accounting:
			from accounts.utils import create_stock_in_hand_jv
			create_stock_in_hand_jv(reverse = \
				cint(self.doc.auto_inventory_accounting) < previous_auto_inventory_accounting)
		
	def on_update(self):
		for key in ["auto_inventory_accounting"]:
			webnotes.conn.set_default(key, self.doc.fields.get(key, ''))
