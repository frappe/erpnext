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

"""will be called by scheduler"""

import webnotes
from webnotes.utils import scheduler
	
def execute_all():
	"""
		* get support email
		* recurring invoice
	"""
	try:
		from support.doctype.support_ticket import get_support_mails
		get_support_mails()
	except Exception, e:
		scheduler.log('get_support_mails')

	try:
		from accounts.doctype.gl_control.gl_control import manage_recurring_invoices
		manage_recurring_invoices()
	except Exception, e:
		scheduler.log('manage_recurring_invoices')

	
	
def execute_daily():
	"""email digest"""
	try:
		from setup.doctype.email_digest.email_digest import send
		send()
	except Exception, e:
		scheduler.log('email_digest.send')

def execute_weekly():
	pass

def execute_monthly():
	pass

def execute_hourly():
	pass
