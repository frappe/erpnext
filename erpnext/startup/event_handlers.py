import webnotes
import webnotes.defs
from webnotes.utils import cint

def on_login(login_manager):
	"""
		called from login manager, before login
	"""
	try:
		if login_manager.user not in ('Guest', None, ''):
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

def doclist_all(doc, method):
	"""doclist trigger called from webnotes.model.doclist on any event"""
	import home
	home.update_feed(doc, method)
	
def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import webnotes
	import webnotes.model.doc
	
	if webnotes.session['user']=='Guest':
		bootinfo['topbar'] = webnotes.model.doc.getsingle('Top Bar Settings')
		bootinfo['topbaritems'] = webnotes.conn.sql("""select label, std_page, custom_page, parent_label
			from `tabTop Bar Item` where parent='Top Bar Settings' order by idx asc""", as_dict=1)
	else:	
		bootinfo['letter_heads'] = get_letter_heads()

def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("select name, content from `tabLetter Head` where ifnull(disabled,0)=0")
	return dict(ret)
