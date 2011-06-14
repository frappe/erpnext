import webnotes

from webnotes.utils import cint, load_json, cstr

try: import json
except: import simplejson as json

def get_account_settings_url(arg=''):
	import server_tools.server_tools.gateway_utils
	return server_tools.server_tools.gateway_utils.get_account_settings_url()

#
# set max users
#
def get_max_users(arg=''):
	from server_tools.server_tools.gateway_utils import get_max_users_gateway
	return {
		'max_users': get_max_users_gateway(),
		'enabled': cint(webnotes.conn.sql("select count(*) from tabProfile where ifnull(enabled,0)=1 and name not in ('Administrator', 'Guest')")[0][0])
	}

#
# enable profile in local
#
def enable_profile(arg=''):
	webnotes.conn.sql("update tabProfile set enabled=1 where name=%s", arg)
	return 1
		
#
# disable profile in local
#
def disable_profile(arg=''):
	if arg=='Administrator':
		return 'Cannot disable Administrator'

	webnotes.conn.sql("update tabProfile set enabled=0 where name=%s", arg)
	return 0

#
# delete user
#
def delete_user(args):
	args = json.loads(args)
	webnotes.conn.sql("update tabProfile set enabled=0, docstatus=2 where name=%s", args['user'])
	# erpnext-saas
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.server_tools.gateway_utils import remove_user_gateway
		remove_user_gateway(args['user'])

#
# add user
#
def add_user(args):
	args = json.loads(args)
	add_profile(args['user'])
	# erpnext-saas
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.server_tools.gateway_utils import add_user_gateway
		add_user_gateway(args['user'])
	
#
# add profile record
#
def add_profile(email):
	from webnotes.utils import validate_email_add
	from webnotes.model.doc import Document
			
	sql = webnotes.conn.sql
	
	if not email:
		email = webnotes.form_dict.get('user')
	if not validate_email_add(email):
		raise Exception
		return 'Invalid Email Id'
	
	if sql("select name from tabProfile where name = %s", email):
		# exists, enable it
		sql("update tabProfile set enabled = 1, docstatus=0 where name = %s", email)
		webnotes.msgprint('Profile exists, enabled it')
	else:
		# does not exist, create it!
		pr = Document('Profile')
		pr.name = email
		pr.email = email
		pr.enabled=1
		pr.user_type='System User'
		pr.save(1)	

#
# post comment
#
def post_comment(arg):
	arg = load_json(arg)
	
	from webnotes.model.doc import Document
	d = Document('Comment Widget Record')
	d.comment_doctype = 'My Company'
	d.comment_docname = arg['uid'] # to
	d.owner = webnotes.user.name
	d.comment = arg['comment']
	d.save(1)
	
	if cint(arg['notify']):
		fn = webnotes.conn.sql('select first_name, last_name from tabProfile where name=%s', webnotes.user.name)[0]
		if fn[0] or f[1]:
			fn = cstr(fn[0]) + (fn[0] and ' ' or '') + cstr(fn[1])
		else:
			fn = webnotes.user.name

		from webnotes.utils.email_lib import sendmail
		from settings.doctype.notification_control.notification_control import get_formatted_message
		
		message = '''A new comment has been posted on your page by %s:
		
		<b>Comment:</b> %s
		
		To answer, please login to your erpnext account!
		''' % (fn, arg['comment'])
		
		sendmail([arg['uid']], webnotes.user.name, get_formatted_message('New Comment', message), fn + ' has posted a new comment')
	
#
# update read messages
#
def set_read_all_messages(arg=''):
	webnotes.conn.sql("""UPDATE `tabComment Widget Record`
	SET docstatus = 1
	WHERE comment_doctype = 'My Company'
	AND comment_docname = %s
	""", webnotes.user.name)
