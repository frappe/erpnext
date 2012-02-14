import webnotes
import webnotes.defs
from webnotes.utils import cint
import home

def on_login(login_manager):
	"""
		called from login manager, before login
	"""
	if login_manager.user not in ('Guest', None, ''):
		try:
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

	if webnotes.session['user'] not in ('Guest'):
		# create feed
		from webnotes.utils import nowtime
		home.make_feed('Login', 'Profile', login_manager.user, login_manager.user,
			'%s logged in at %s' % (login_manager.user_fullname, nowtime()), 
			login_manager.user=='Administrator' and '#8CA2B3' or '#1B750D')		

def comment_added(doc):
	"""add comment to feed"""
	home.make_feed('Comment', doc.comment_doctype, doc.comment_docname, doc.comment_by,
		'<i>"' + doc.comment + '"</i>', '#6B24B3')

def doclist_all(doc, method):
	"""doclist trigger called from webnotes.model.doclist on any event"""
	home.update_feed(doc, method)
	
def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	import webnotes
	import webnotes.model.doc
	
	if webnotes.session['user']=='Guest':
		bootinfo['website_settings'] = webnotes.model.doc.getsingle('Website Settings')
		bootinfo['website_menus'] = webnotes.conn.sql("""select label, url, custom_page, 
			parent_label, parentfield
			from `tabTop Bar Item` where parent='Website Settings' order by idx asc""", as_dict=1)
		bootinfo['custom_css'] = webnotes.conn.get_value('Style Settings', None, 'custom_css') or ''
		bootinfo['analytics_code'] = \
			webnotes.conn.get_value('Website Settings', None, 'analytics_code')
		bootinfo['analytics_call'] = \
			webnotes.conn.get_value('Website Settings', None, 'analytics_call')
	else:	
		bootinfo['letter_heads'] = get_letter_heads()

def get_letter_heads():
	"""load letter heads with startup"""
	import webnotes
	ret = webnotes.conn.sql("""select name, content from `tabLetter Head` 
		where ifnull(disabled,0)=0""")
	return dict(ret)
