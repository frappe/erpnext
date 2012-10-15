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
from webnotes.utils import cint
import home

		
def on_login_post_session(login_manager):
	"""
		called after login
		update login_from and delete parallel sessions
	"""
	# Clear previous sessions i.e. logout previous log-in attempts
	exception_list = ['demo@webnotestech.com', 'Administrator', 'Guest']
	if webnotes.session['user'] not in exception_list:
		sid_list = webnotes.conn.sql("""
			DELETE FROM `tabSessions`
			WHERE
				user=%s AND
				sid!=%s""", \
			(webnotes.session['user'], webnotes.session['sid']), as_list=1)

		# check if account is expired
		check_if_expired()

	if webnotes.session['user'] not in ('Guest', 'demo@webnotestech.com'):
		# create feed
		from webnotes.utils import nowtime
		from webnotes.profile import get_user_fullname
		home.make_feed('Login', 'Profile', login_manager.user, login_manager.user,
			'%s logged in at %s' % (get_user_fullname(login_manager.user), nowtime()), 
			login_manager.user=='Administrator' and '#8CA2B3' or '#1B750D')		


def comment_added(doc):
	"""add comment to feed"""
	home.make_feed('Comment', doc.comment_doctype, doc.comment_docname, doc.comment_by,
		'<i>"' + doc.comment + '"</i>', '#6B24B3')

def doclist_all(doc, method):
	"""doclist trigger called from webnotes.model.doclist on any event"""
	home.update_feed(doc, method)
	
def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import webnotes
	import webnotes.model.doc
	
	bootinfo['custom_css'] = webnotes.conn.get_value('Style Settings', None, 'custom_css') or ''
	bootinfo['website_settings'] = webnotes.model.doc.getsingle('Website Settings')

	if webnotes.session['user']=='Guest':
		bootinfo['website_menus'] = webnotes.conn.sql("""select label, url, custom_page, 
			parent_label, parentfield
			from `tabTop Bar Item` where parent='Website Settings' order by idx asc""", as_dict=1)
		bootinfo['startup_code'] = \
			webnotes.conn.get_value('Website Settings', None, 'startup_code')
	else:	
		bootinfo['letter_heads'] = get_letter_heads()

		import webnotes.model.doctype
		bootinfo['docs'] += webnotes.model.doctype.get('Event')
		bootinfo['docs'] += webnotes.model.doctype.get('Search Criteria')
		
		bootinfo['modules_list'] = webnotes.conn.get_global('modules_list')
		
		# if no company, show a dialog box to create a new company
		bootinfo['setup_complete'] = webnotes.conn.sql("""select name from 
			tabCompany limit 1""") and 'Yes' or 'No'
			
		bootinfo['user_background'] = webnotes.conn.get_value("Profile", webnotes.session['user'], 'background_image') or ''
		
		# load subscription info
		import conf
		for key in ['max_users', 'expires_on', 'max_space', 'status', 'developer_mode']:
			if hasattr(conf, key): bootinfo[key] = getattr(conf, key)

		company = webnotes.conn.sql("select name, default_currency from `tabCompany`", as_dict=1)
		company_dict = {}
		for c in company:
			company_dict.setdefault(c['name'], {}).update(c)

		bootinfo['company'] = company_dict
		
def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)
	

def check_if_expired():
	"""check if account is expired. If expired, do not allow login"""
	import conf
	# check if expires_on is specified
	if not hasattr(conf, 'expires_on'): return
	
	# check if expired
	from datetime import datetime, date
	expires_on = datetime.strptime(conf.expires_on, '%Y-%m-%d').date()
	if date.today() <= expires_on: return
	
	# if expired, stop user from logging in
	from webnotes.utils import formatdate
	msg = """Oops! Your subscription expired on <b>%s</b>.<br>""" % formatdate(conf.expires_on)
	
	if 'System Manager' in webnotes.user.roles:
		msg += """Just drop in a mail at <b>support@erpnext.com</b> and
			we will guide you to get your account re-activated."""
	else:
		msg += """Just ask your System Manager to drop in a mail at <b>support@erpnext.com</b> and
		we will guide him to get your account re-activated."""
	
	webnotes.msgprint(msg)
	
	webnotes.response['message'] = 'Account Expired'
	raise webnotes.AuthenticationError

#### website

def get_web_script():
	"""returns web startup script"""
	return webnotes.conn.get_value('Website Settings', None, 'startup_code') or ''

def get_web_style():
	"""returns web css"""
	return webnotes.conn.get_value('Style Settings', None, 'custom_css') or ''

def get_web_header(page_name):
	"""get website header"""
	from website.utils import get_header
	return get_header(page_name)

def get_web_footer(page_name):
	"""get website footer"""
	from website.utils import get_footer
	return get_footer(page_name)
