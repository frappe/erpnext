# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt"


from __future__ import unicode_literals
import frappe
from erpnext.home import make_feed

def on_session_creation(login_manager):
	"""make feed"""
	if frappe.session['user'] not in ('Guest'):
		# create feed
		from frappe.utils import nowtime
		from frappe.utils.user import get_user_fullname
		make_feed('Login', 'User', login_manager.user, login_manager.user,
			'%s logged in at %s' % (get_user_fullname(login_manager.user), nowtime()), 
			login_manager.user=='Administrator' and '#8CA2B3' or '#1B750D')
