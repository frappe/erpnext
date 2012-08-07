from __future__ import unicode_literals
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
