# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes import msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def get_message(self, arg):
		fn = arg.lower().replace(' ', '_') + '_message'
		v = sql("select value from tabSingles where field=%s and doctype=%s", (fn, 'Notification Control'))
		return v and v[0][0] or ''

	def set_message(self, arg = ''):
		fn = self.doc.select_transaction.lower().replace(' ', '_') + '_message'
		webnotes.conn.set(self.doc, fn, self.doc.custom_message)
		msgprint("Custom Message for %s updated!" % self.doc.select_transaction)

