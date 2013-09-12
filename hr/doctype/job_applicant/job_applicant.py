# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from utilities.transaction_base import TransactionBase
from webnotes.utils import extract_email_id

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def get_sender(self, comm):
		return webnotes.conn.get_value('Jobs Email Settings',None,'email_id')
		
	def on_communication(self, comm):
		if webnotes.conn.get_value("Profile", extract_email_id(comm.sender), "user_type")=="System User":
			status = "Replied"
		else:
			status = "Open"
			
		webnotes.conn.set(self.doc, 'status', status)