# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr
from webnotes import msgprint, _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		self.validate_auto_accounting_for_stock()
		
	def validate_auto_accounting_for_stock(self):
		if cint(self.doc.auto_accounting_for_stock) == 1:
			previous_val = cint(webnotes.conn.get_value("Accounts Settings", 
				None, "auto_accounting_for_stock"))
			if cint(self.doc.auto_accounting_for_stock) != previous_val:
				from accounts.utils import validate_stock_and_account_balance, \
					create_stock_in_hand_jv
				validate_stock_and_account_balance()
				create_stock_in_hand_jv(reverse=cint(self.doc.auto_accounting_for_stock) < previous_val)
	
	def on_update(self):
		for key in ["auto_accounting_for_stock"]:
			webnotes.conn.set_default(key, self.doc.fields.get(key, ''))
