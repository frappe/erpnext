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
			
	ret = {
		'user_count': len(online) or 0, 
		'unread_messages': get_unread_messages(),
		'online_users': online or [],
		'system_message':msg,
		'is_trial': webnotes.conn.get_global('is_trial'),
		'days_to_expiry': (webnotes.conn.get_global('days_to_expiry') or '0'),
		'setup_status': get_setup_status()
	}
	return ret

def get_setup_status():
	"""
		Returns the setup status of the current account
	"""
	if cint(webnotes.conn.get_global('setup_done')):
		return ''
		
	percent = 20
	ret = []
	
	if not webnotes.conn.get_value('Personalize', None, 'header_html'):
		ret.append('<a href="#!Form/Personalize/Personalize">Upload your company banner</a>')
	else:
		percent += 20
	
	def check_type(doctype, ret, percent):	
		if not webnotes.conn.sql("select count(*) from tab%s" % doctype)[0][0]:
			ret.append('''
				<a href="#!Form/%(dt)s/New">
				Create a new %(dt)s
				</a> or 
				<a href="#!Import Data/%(dt)s">
				Import from a spreadsheet</a>''' % {'dt':doctype})
		else:
			percent += 20
		return ret, percent

	ret, percent = check_type('Item', ret, percent)
	ret, percent = check_type('Customer', ret, percent)
	ret, percent = check_type('Supplier', ret, percent)
	
	if percent==100:
		webnotes.conn.set_global('setup_done', '1')
		return ''
		
	return {'ret': ret, 'percent': percent}
		