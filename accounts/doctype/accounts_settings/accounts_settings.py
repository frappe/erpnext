# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr
from webnotes import msgprint, _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def validate(self):
		self.validate_perpetual_accounting()
		
	def validate_perpetual_accounting(self):
		if cint(self.doc.perpetual_accounting) == 1:
			previous_val = cint(webnotes.conn.get_value("Accounts Settings", 
				None, "perpetual_accounting"))
			if cint(self.doc.perpetual_accounting) != previous_val:
				from accounts.utils import validate_stock_and_account_balance
				validate_stock_and_account_balance()
	
	def on_update(self):
		for key in ["perpetual_accounting"]:
			webnotes.conn.set_default(key, self.doc.fields.get(key, ''))
