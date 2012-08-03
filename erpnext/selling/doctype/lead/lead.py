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
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

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
	
	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')
	
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
		import string		
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
		if self.doc.contact_by:
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
	
		in_calendar_of = self.doc.lead_owner
		
		# get profile (id) if exists for contact_by
		email_id = webnotes.conn.get_value('Sales Person', self.doc.contact_by, 'email_id')
		if webnotes.conn.exists('Profile', email_id):
			in_calendar_of = email_id
		
		ev = Document('Event')
		ev.owner = in_calendar_of
		ev.description = 'Contact ' + cstr(self.doc.lead_name) + '.By : ' + cstr(self.doc.contact_by) + '.To Discuss : ' + cstr(self.doc.remark)
		ev.event_date = self.doc.contact_date
		ev.event_hour = '10:00'
		ev.event_type = 'Private'
		ev.ref_type = 'Lead'
		ev.ref_name = self.doc.name
		ev.save(1)

	def add_in_follow_up(self,message,type):
		import datetime
		child = addchild( self.doc, 'follow_up', 'Communication Log', 1, self.doclist)
		child.date = datetime.datetime.now().date().strftime('%Y-%m-%d')
		child.notes = message
		child.follow_up_type = type
		child.save()

#-------------------SMS----------------------------------------------
	def send_sms(self):
		if not self.doc.sms_message or not self.doc.mobile_no:
			msgprint("Please enter mobile number in Basic Info Section and message in SMS Section ")
			raise Exception
		else:
			receiver_list = []
			if self.doc.mobile_no:
				receiver_list.append(self.doc.mobile_no)
			for d in getlist(self.doclist,'lead_sms_detail'):
				if d.other_mobile_no:
					receiver_list.append(d.other_mobile_no)
		
		if receiver_list:
			msgprint(get_obj('SMS Control', 'SMS Control').send_sms(receiver_list, self.doc.sms_message))
			self.add_in_follow_up(self.doc.sms_message,'SMS')
