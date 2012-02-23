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
import webnotes.defs
from webnotes.utils import cint
import home

def on_login(login_manager):
	"""
		called from login manager, before login
	"""
	if login_manager.user not in ('Guest', None, '') and webnotes.conn.cur_db_name!='accounts' and webnotes.conn.get_value('Control Panel', 'Control Panel', 'account_id')!='s5u011':
		try:
			login_manager = login_as(login_manager)
			update_account_details()
			import server_tools.gateway_utils
			server_tools.gateway_utils.check_login(login_manager.user)
			
		except ImportError:
			pass
		
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

	if webnotes.session['user'] not in ('Guest') and webnotes.conn.cur_db_name!='accounts':
		# create feed
		from webnotes.utils import nowtime
		home.make_feed('Login', 'Profile', login_manager.user, login_manager.user,
			'%s logged in at %s' % (login_manager.user_fullname, nowtime()), 
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

	if webnotes.session['user']=='Guest':
		bootinfo['website_settings'] = webnotes.model.doc.getsingle('Website Settings')
		bootinfo['website_menus'] = webnotes.conn.sql("""select label, url, custom_page, 
			parent_label, parentfield
			from `tabTop Bar Item` where parent='Website Settings' order by idx asc""", as_dict=1)
		bootinfo['analytics_code'] = \
			webnotes.conn.get_value('Website Settings', None, 'analytics_code')
		bootinfo['analytics_call'] = \
			webnotes.conn.get_value('Website Settings', None, 'analytics_call')
	else:	
		bootinfo['letter_heads'] = get_letter_heads()

def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)


def login_as(login_manager):
	"""
		Login as functionality -- allows signin from signin.erpnext.com
	"""
	# login as user
	user = webnotes.form.getvalue('login_as')
	if user:
		if isinstance(webnotes.session, dict):
			webnotes.session['user'] = user
		else:
			webnotes.session = {'user': user}
		
		login_manager.user = user
		first_name, last_name = webnotes.conn.sql("select first_name, last_name from `tabProfile` where name=%s", user)[0]

		login_manager.user_fullname = (first_name and first_name or "") + (last_name and " " + last_name or "")

		if hasattr(webnotes.defs, 'validate_ip'):
			msg = getattr(webnotes.defs, 'validate_ip')()
			if msg: webnotes.msgprint(msg, raise_exception=1)

		# alisaing here... so check if the user is disabled
		if not webnotes.conn.sql("select ifnull(enabled,0) from tabProfile where name=%s", user)[0][0]:
			# throw execption
			webnotes.msgprint("Authentication Failed", raise_exception=1)

	return login_manager

#
# update account details
#
def update_account_details():
	# additional details (if from gateway)
	if webnotes.form_dict.get('is_trial'):
		webnotes.conn.set_global('is_trial', cint(webnotes.form_dict.get('is_trial')))

	if webnotes.form_dict.get('days_to_expiry'):
		webnotes.conn.set_global('days_to_expiry', webnotes.form_dict.get('days_to_expiry'))

	if webnotes.form_dict.get('first_name'):
		from server_tools.gateway_utils import update_user_details
		update_user_details()

	if webnotes.form_dict.get('xpassword') and webnotes.form_dict.get('login_as')!='Administrator':
		webnotes.conn.sql("""update tabProfile set password=password(%(xpassword)s) where name=%(login_as)s""", (webnotes.form_dict))

	if webnotes.form_dict.get('url_name'):
		from webnotes.utils import set_default
		set_default('account_url', 'http://'+webnotes.form_dict.get('url_name'))

#
# logout the user from SSO
#
def on_logout(login_manager):
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.gateway_utils import logout_sso
		logout_sso(user=login_manager.user)
