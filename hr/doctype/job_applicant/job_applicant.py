# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def get_sender(self, comm):
		return webnotes.conn.get_value('Jobs Email Settings',None,'email_id')
		
	def on_communication_sent(self, comm):
		webnotes.conn.set(self.doc, 'status', 'Replied')

	def on_trash(self):
		webnotes.conn.sql("""delete from `tabCommunication` 
			where job_applicant=%s""", self.doc.name)
		