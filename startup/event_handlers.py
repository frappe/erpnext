# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


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
		
	if webnotes.conn.get_value("Profile", webnotes.session.user, "user_type") == "Website User":
		from selling.utils.cart import set_cart_count
		set_cart_count()
		
def on_logout(login_manager):
	webnotes._response.set_cookie("cart_count", "")
		
def check_if_expired():
	"""check if account is expired. If expired, do not allow login"""
	from webnotes import conf
	# check if expires_on is specified
	if not 'expires_on' in conf: return
	
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

def on_build():
	from home.page.latest_updates import latest_updates
	latest_updates.make()

def comment_added(doc):
	"""add comment to feed"""
	home.make_feed('Comment', doc.comment_doctype, doc.comment_docname, doc.comment_by,
		'<i>"' + doc.comment + '"</i>', '#6B24B3')
	
