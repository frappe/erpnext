import webnotes
from webnotes.utils import cint

def get_online_users():
	# get users
	return webnotes.conn.sql("""SELECT DISTINCT t1.user, t2.first_name, t2.last_name 
		from tabSessions t1, tabProfile t2
		where t1.user = t2.name
		and t1.user not in ('Guest','Administrator')
		and TIMESTAMPDIFF(HOUR,t1.lastupdate,NOW()) <= 1""", as_list=1) or []

#
# get unread messages
#
def get_unread_messages():
	"returns unread (docstatus-0 messages for a user)"
	return cint(webnotes.conn.sql("""SELECT COUNT(*) FROM `tabComment Widget Record`
	WHERE comment_doctype='My Company'
	AND comment_docname = %s
	AND ifnull(docstatus,0)=0
	""", webnotes.user.name)[0][0])

#
# Get toolbar items
#	
def get_status_details(arg=None):
	from webnotes.utils import cint, date_diff, nowdate
		
	online = get_online_users()
			
	# system messages
	msg_id = webnotes.conn.get_global('system_message_id')
	msg = ''
				
	if msg_id and msg_id != webnotes.conn.get_global('system_message_id', webnotes.session['user']):
		msg = webnotes.conn.get_global('system_message')
			
	return {
		'user_count': len(online) or 0, 
		'unread_messages': get_unread_messages(),
		'online_users': online or [],
		'system_message':msg,
		'is_trial': webnotes.conn.get_global('is_trial'),
		'days_to_expiry': (webnotes.conn.get_global('days_to_expiry') or '0')
	}

#
# Convert to a paid account
#	
def convert_to_paid():
	from server_tools.server_tools.gateway_utils import convert_to_paid_gateway
	r = convert_to_paid_gateway()
	if r['exc']:
		webnotes.msgprint(r['exc'])
		raise Exception, r['exc']
	webnotes.msgprint('Thank you for choosing to convert to a Paid Account!')	
