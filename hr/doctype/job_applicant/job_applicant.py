# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def onload(self):
		self.add_communication_list()
		
	def on_communication_sent(self, comm):
		webnotes.conn.set(self.doc, 'status', 'Replied')
		