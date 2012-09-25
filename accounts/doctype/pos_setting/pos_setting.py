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

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc, self.doclist = doc,doclist

	#--------------------get naming series from sales invoice-----------------
	def get_series(self):
		import webnotes.model.doctype
		docfield = webnotes.model.doctype.get('Sales Invoice')
		series = [d.options for d in docfield if d.doctype == 'DocField' and d.fieldname == 'naming_series']
		return series and series[0] or ''

	def validate(self):
		res = sql("select name, user from `tabPOS Setting` where ifnull(user, '') = '%s' and name != '%s' and company = '%s'" % (self.doc.user, self.doc.name, self.doc.company))
		if res:
			if res[0][1]:
				msgprint("POS Setting '%s' already created for user: '%s' and company: '%s'"%(res[0][0], res[0][1], self.doc.company), raise_exception=1)
			else:
				msgprint("Global POS Setting already created - %s for this company: '%s'" % (res[0][0], self.doc.company), raise_exception=1)
