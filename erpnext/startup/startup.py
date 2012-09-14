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

def get_unread_messages():
	"returns unread (docstatus-0 messages for a user)"
	return webnotes.conn.sql("""\
		SELECT name, comment
		FROM `tabComment`
		WHERE comment_doctype IN ('My Company', 'Message')
		AND comment_docname = %s
		AND ifnull(docstatus,0)=0
		""", webnotes.user.name, as_list=1)

def get_open_support_tickets():
	"""Returns a count of open support tickets"""
	from webnotes.utils import cint
	open_support_tickets = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabSupport Ticket`
		WHERE status = 'Open'""")
	return open_support_tickets and cint(open_support_tickets[0][0]) or 0

def get_open_tasks():
	"""Returns a count of open tasks"""
	from webnotes.utils import cint
	return webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabTask`
		WHERE status = 'Open'""")[0][0]

def get_things_todo():
	"""Returns a count of incomplete todos"""
	from webnotes.utils import cint
	incomplete_todos = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabToDo`
		WHERE IFNULL(checked, 0) = 0
		AND owner = %s""", webnotes.session.get('user'))
	return incomplete_todos and cint(incomplete_todos[0][0]) or 0

def get_todays_events():
	"""Returns a count of todays events in calendar"""
	from webnotes.utils import nowdate, cint
	todays_events = webnotes.conn.sql("""\
		SELECT COUNT(*) FROM `tabEvent`
		WHERE owner = %s
		AND event_type != 'Cancel'
		AND event_date = %s""", (
		webnotes.session.get('user'), nowdate()))
	return todays_events and cint(todays_events[0][0]) or 0

def get_unanswered_questions():
	return len(filter(lambda d: d[0]==0,
		webnotes.conn.sql("""select (select count(*) from tabAnswer 
		where tabAnswer.question = tabQuestion.name) as answers from tabQuestion""")))
	
@webnotes.whitelist()
def get_global_status_messages(arg=None):
	return {
		'unread_messages': get_unread_messages(),
		'open_support_tickets': get_open_support_tickets(),
		'things_todo': get_things_todo(),
		'todays_events': get_todays_events(),
		'open_tasks': get_open_tasks(),
		'unanswered_questions': get_unanswered_questions()
	}
