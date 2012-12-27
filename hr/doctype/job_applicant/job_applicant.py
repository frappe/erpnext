# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, validate_email_add
from webnotes.model.doc import Document, addchild
from webnotes import session, msgprint

sql = webnotes.conn.sql
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def onload(self):
		self.add_communication_list();