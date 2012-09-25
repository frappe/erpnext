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

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.utils.email_lib import sendmail
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

sql = webnotes.conn.sql

# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_project_details(self):
		cust = sql("select customer, customer_name from `tabProject` where name = %s", self.doc.project)
		if cust:
			ret = {'customer': cust and cust[0][0] or '', 'customer_name': cust and cust[0][1] or ''}
			return ret
	
	def get_customer_details(self):
		cust = sql("select customer_name from `tabCustomer` where name=%s", self.doc.customer)
		if cust:
			ret = {'customer_name': cust and cust[0][0] or ''}
			return ret

	def validate(self):
		if self.doc.exp_start_date and self.doc.exp_end_date and getdate(self.doc.exp_start_date) > getdate(self.doc.exp_end_date):
			msgprint("'Expected Start Date' can not be greater than 'Expected End Date'")
			raise Exception
		
		if self.doc.act_start_date and self.doc.act_end_date and getdate(self.doc.act_start_date) > getdate(self.doc.act_end_date):
			msgprint("'Actual Start Date' can not be greater than 'Actual End Date'")
			raise Exception

