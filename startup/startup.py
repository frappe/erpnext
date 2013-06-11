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

def get_unread_messages():
	"returns unread (docstatus-0 messages for a user)"
	return webnotes.conn.sql("""\
		SELECT count(*)
		FROM `tabComment`
		WHERE comment_doctype IN ('My Company', 'Message')
		AND comment_docname = %s
		AND ifnull(docstatus,0)=0
		""", webnotes.user.name)[0][0]

def get_open_support_tickets():
	"""Returns a count of open support tickets"""
	open_support_tickets = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabSupport Ticket`
		WHERE status = 'Open'""")
	return open_support_tickets[0][0]

def get_open_tasks():
	"""Returns a count of open tasks"""
	return webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabTask`
		WHERE status = 'Open'""")[0][0]

def get_things_todo():
	"""Returns a count of incomplete todos"""
	incomplete_todos = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabToDo`
		WHERE IFNULL(checked, 0) = 0
		AND (owner = %s or assigned_by=%s)""", (webnotes.session.user, webnotes.session.user))
	return incomplete_todos[0][0]

def get_todays_events():
	"""Returns a count of todays events in calendar"""
	from webnotes.utils import nowdate
	todays_events = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabEvent`
		WHERE owner = %s
		AND event_type != 'Cancel'
		AND %s between date(starts_on) and date(ends_on)""", (
		webnotes.session.user, nowdate()))
	return todays_events[0][0]

def get_open_leads():
	return webnotes.conn.sql("""select count(*) from tabLead 
		where status='Open'""")[0][0]
	
@webnotes.whitelist()
def get_global_status_messages(arg=None):
	return {
		'unread_messages': get_unread_messages(),
		'open_support_tickets': get_open_support_tickets(),
		'things_todo': get_things_todo(),
		'todays_events': get_todays_events(),
		'open_tasks': get_open_tasks(),
		'open_leads': get_open_leads()
	}
