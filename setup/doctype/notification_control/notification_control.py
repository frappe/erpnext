# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes import msgprint


class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def get_message(self, arg):
		fn = arg.lower().replace(' ', '_') + '_message'
		v = webnotes.conn.sql("select value from tabSingles where field=%s and doctype=%s", (fn, 'Notification Control'))
		return v and v[0][0] or ''

	def set_message(self, arg = ''):
		fn = self.doc.select_transaction.lower().replace(' ', '_') + '_message'
		webnotes.conn.set(self.doc, fn, self.doc.custom_message)
		msgprint("Custom Message for %s updated!" % self.doc.select_transaction)

