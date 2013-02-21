# ERPNext: Copyright 2013 Web Notes Technologies Pvt Ltd
# GNU General Public License. See "license.txt"


from __future__ import unicode_literals
import webnotes
import home

		
def on_login_post_session(login_manager):
	"""
		called after login
		update login_from and delete parallel sessions
	"""
	# Clear previous sessions i.e. logout previous log-in attempts
	allow_multiple_sessions = ['demo@erpnext.com', 'Administrator', 'Guest']
	if webnotes.session['user'] not in allow_multiple_sessions:
		from webnotes.sessions import clear_sessions
		clear_sessions(webnotes.session.user, keep_current=True)

		# check if account is expired
		check_if_expired()

	if webnotes.session['user'] not in ('Guest', 'demo@erpnext.com'):
		# create feed
		from webnotes.utils import nowtime
		from webnotes.profile import get_user_fullname
		webnotes.conn.begin()
		home.make_feed('Login', 'Profile', login_manager.user, login_manager.user,
			'%s logged in at %s' % (get_user_fullname(login_manager.user), nowtime()), 
			login_manager.user=='Administrator' and '#8CA2B3' or '#1B750D')
		webnotes.conn.commit()


def comment_added(doc):
	"""add comment to feed"""
	home.make_feed('Comment', doc.comment_doctype, doc.comment_docname, doc.comment_by,
		'<i>"' + doc.comment + '"</i>', '#6B24B3')
	
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
		bootinfo['notification_settings'] = webnotes.doc("Notification Control", 
			"Notification Control").get_values()
		
		bootinfo['modules_list'] = webnotes.conn.get_global('modules_list')
		
		# if no company, show a dialog box to create a new company
		bootinfo['setup_complete'] = webnotes.conn.sql("""select name from 
			tabCompany limit 1""") and 'Yes' or 'No'
		
		# load subscription info
		import conf
		for key in ['max_users', 'expires_on', 'max_space', 'status', 'developer_mode']:
			if hasattr(conf, key): bootinfo[key] = getattr(conf, key)

		bootinfo['docs'] += webnotes.conn.sql("select name, default_currency from `tabCompany`", 
			as_dict=1, update={"doctype":":Company"})
			
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
	
	if 'System Manager' in webnotes.user.get_roles():
		msg += """Just drop in a mail at <b>support@erpnext.com</b> and
			we will guide you to get your account re-activated."""
	else:
		msg += """Just ask your System Manager to drop in a mail at <b>support@erpnext.com</b> and
		we will guide him to get your account re-activated."""
	
	webnotes.msgprint(msg)
	
	webnotes.response['message'] = 'Account Expired'
	raise webnotes.AuthenticationError
