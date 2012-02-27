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

import webnotes
from webnotes.utils import cint

@webnotes.whitelist()
def get_online_users(arg=None):
	# get users
	return webnotes.conn.sql("""SELECT DISTINCT t1.user, t2.first_name, t2.last_name 
		from tabSessions t1, tabProfile t2
		where t1.user = t2.name
		and t1.user not in ('Guest','Administrator')
		and TIMESTAMPDIFF(HOUR,t1.lastupdate,NOW()) <= 1""", as_list=1) or []

@webnotes.whitelist()
def get_unread_messages(arg=None):
	"returns unread (docstatus-0 messages for a user)"
	return webnotes.conn.sql("""\
		SELECT name, comment
		FROM `tabComment Widget Record`
		WHERE comment_doctype IN ('My Company', 'Message')
		AND comment_docname = %s
		AND ifnull(docstatus,0)=0
		""", webnotes.user.name, as_list=1)

@webnotes.whitelist()
def get_status_details(arg=None):
	"""get toolbar items"""
	from webnotes.utils import cint, date_diff, nowdate, get_defaults
		
	online = get_online_users()
			
	# system messages			
	ret = {
		'user_count': len(online) or 0, 
		'unread_messages': get_unread_messages(),
		'online_users': online or [],
		'setup_status': get_setup_status(),
		'registration_complete': cint(get_defaults('registration_complete')) and 'Yes' or 'No',
		'profile': webnotes.conn.sql("""\
			SELECT first_name, last_name FROM `tabProfile`
			WHERE name=%s AND docstatus<2""", webnotes.user.name, as_dict=1)
	}
	return ret

def get_setup_status(arg=None):
	"""
		Returns the setup status of the current account
	"""
	if cint(webnotes.conn.get_global('setup_done')):
		return ''
		
	percent = 20
	ret = []
	
	def is_header_set():
		header = webnotes.conn.get_value('Control Panel', None, 'client_name') or ''

		if header.startswith('<div style="padding:4px; font-size:20px;">'\
			+(webnotes.conn.get_value('Control Panel', None, 'company_name') or '')):
			return False
			
		elif 'Banner Comes Here' in header:
			return False
			
		else:
			return True
	
	if not is_header_set():
		ret.append('<a href="#!Form/Personalize/Personalize">Upload your company banner</a>')
	else:
		percent += 20
	
	def check_type(doctype, ret, percent):	
		if not webnotes.conn.sql("select count(*) from tab%s" % doctype)[0][0]:
			ret.append('''
				<a href="#!Form/%(dt)s/New">
				Create a new %(dt)s
				</a> or 
				<a href="#!Import Data/%(dt)s">
				Import from a spreadsheet</a>''' % {'dt':doctype})
		else:
			percent += 20
		return ret, percent

	ret, percent = check_type('Item', ret, percent)
	ret, percent = check_type('Customer', ret, percent)
	ret, percent = check_type('Supplier', ret, percent)
	
	if percent==100:
		webnotes.conn.set_global('setup_done', '1')
		return ''
		
	return {'ret': ret, 'percent': percent}
		
