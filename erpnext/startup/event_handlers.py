import webnotes
import webnotes.defs
from webnotes.utils import cint

def on_login(login_manager):
	"""
		called from login manager, before login
	"""
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
	exception_list = ['demo@webnotestech.com', 'Administrator']
	if webnotes.session['user'] not in exception_list:
		sid_list = webnotes.conn.sql("""
			DELETE FROM `tabSessions`
			WHERE
				user=%s AND
				sid!=%s""", \
			(webnotes.session['user'], webnotes.session['sid']), as_list=1)
