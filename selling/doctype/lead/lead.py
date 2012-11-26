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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.wrapper import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
	
	#check status of lead
	#------------------------
	def check_status(self):
		chk = sql("select status from `tabLead` where name=%s", self.doc.name)
		chk = chk and chk[0][0] or ''
		return cstr(chk)


	# Get item detail (will be removed later)
	#=======================================
	def get_item_detail(self,item_code):
		it=sql("select item_name,brand,item_group,description,stock_uom from `tabItem` where name='%s'"%item_code)
		if it:
			ret = {
			'item_name'	: it and it[0][0] or '',
			'brand'			: it and it[0][1] or '',
			'item_group' : it and it[0][2] or '',
			'description': it and it[0][3] or '',
			'uom' : it and it[0][4] or ''
			}
			return ret
	
	def validate(self):
		if self.doc.status == 'Lead Lost' and not self.doc.order_lost_reason:
			msgprint("Please Enter Lost Reason under More Info section")
			raise Exception	
		
		if self.doc.source == 'Campaign' and not self.doc.campaign_name and session['user'] != 'Guest':
			msgprint("Please specify campaign name")
			raise Exception
		
		if self.doc.email_id:
			if not validate_email_add(self.doc.email_id):
				msgprint('Please enter valid email id.')
				raise Exception
	
	def on_update(self):
		if self.doc.contact_date:
			self.add_calendar_event()
		
		if not self.doc.naming_series:
			if session['user'] == 'Guest':
				import webnotes.model.doctype
				docfield = webnotes.model.doctype.get('Lead')
				series = [d.options for d in docfield if d.doctype == 'DocField' and d.fieldname == 'naming_series']
				if series:
					sr = series[0].split("\n")
					set(self.doc, 'naming_series', sr[0])
			else:
				msgprint("Please specify naming series")
				raise Exception

	# Add to Calendar
	# ===========================================================================
	def add_calendar_event(self):
		# delete any earlier event by this lead
		sql("delete from tabEvent where ref_type='Lead' and ref_name=%s", self.doc.name)
	
		# create new event
		ev = Document('Event')
		ev.owner = self.doc.lead_owner
		ev.description = ('Contact ' + cstr(self.doc.lead_name)) + \
			(self.doc.contact_by and ('. By : ' + cstr(self.doc.contact_by)) or '') + \
			(self.doc.remark and ('.To Discuss : ' + cstr(self.doc.remark)) or '')
		ev.event_date = self.doc.contact_date
		ev.event_hour = '10:00'
		ev.event_type = 'Private'
		ev.ref_type = 'Lead'
		ev.ref_name = self.doc.name
		ev.save(1)
		
		event_user = addchild(ev, 'event_individuals', 'Event User')
		event_user.person = self.doc.contact_by
		event_user.save()
