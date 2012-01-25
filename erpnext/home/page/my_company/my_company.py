import webnotes

from webnotes.utils import cint, load_json, cstr
from webnotes.model.doc import Document

try: import json
except: import simplejson as json

def get_account_settings_url(arg=''):
	import server_tools.gateway_utils
	return server_tools.gateway_utils.get_account_settings_url()

#
# set max users
#
def get_max_users(arg=''):
	from server_tools.gateway_utils import get_max_users_gateway
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
	webnotes.login_manager.logout(user=arg)
	return 0

#
# delete user
#
def delete_user(args):
	args = json.loads(args)
	webnotes.conn.sql("update tabProfile set enabled=0, docstatus=2 where name=%s", args['user'])
	# erpnext-saas
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.gateway_utils import remove_user_gateway
		remove_user_gateway(args['user'])

#
# add user
#
def add_user(args):
	args = json.loads(args)
	# erpnext-saas
	if cint(webnotes.conn.get_value('Control Panel', None, 'sync_with_gateway')):
		from server_tools.gateway_utils import add_user_gateway
		add_user_gateway(args['user'])
	
	add_profile(args)
	
#
# add profile record
#
def add_profile(args):
	from webnotes.utils import validate_email_add, now
	email = args['user']
			
	sql = webnotes.conn.sql
	
	if not email:
		email = webnotes.form_dict.get('user')
	if not validate_email_add(email):
		raise Exception
		return 'Invalid Email Id'
	
	if sql("select name from tabProfile where name = %s", email):
		# exists, enable it
		sql("update tabProfile set enabled = 1, docstatus=0 where name = %s", email)
		webnotes.msgprint('Profile exists, enabled it with new password')
	else:
		# does not exist, create it!
		pr = Document('Profile')
		pr.name = email
		pr.email = email
		pr.first_name = args.get('first_name')
		pr.last_name = args.get('last_name')
		pr.enabled = 1
		pr.user_type = 'System User'
		pr.save(1)

	if args.get('password'):
		sql("""
			UPDATE tabProfile 
			SET password = PASSWORD(%s), modified = %s
			WHERE name = %s""", (args.get('password'), now, email))

	send_welcome_mail(email, args)

def send_welcome_mail(email, args):
	"""send welcome mail to user with password and login url"""
	pr = Document('Profile', email)
	from webnotes.utils.email_lib import sendmail_md
	args.update({
		'company': webnotes.conn.get_default('company'),
		'password': password,
		'account_url': webnotes.conn.get_default('account_url')
	})
	sendmail_md(pr.email, subject="Welcome to ERPNext", msg=welcome_txt % args)

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

		message = '''A new comment has been posted on your page by %s:
		
		<b>Comment:</b> %s
		
		To answer, please login to your erpnext account!

		<a href='https://signin.erpnext.com'>https://signin.erpnext.com</a>
		''' % (fn, arg['comment'])
		
		from webnotes.model.code import get_obj
		note = get_obj('Notification Control')
		email_msg = note.prepare_message({
			'type': 'New Comment',
			'message': message
		})

		sender = webnotes.user.name!='Administrator' and webnotes.user.name or 'support+admin_post@erpnext.com'
		
		from webnotes.utils.email_lib import sendmail
		sendmail([arg['uid']], sender, email_msg, fn + ' has posted a new comment')
	
#
# update read messages
#
def set_read_all_messages(arg=''):
	webnotes.conn.sql("""UPDATE `tabComment Widget Record`
	SET docstatus = 1
	WHERE comment_doctype = 'My Company'
	AND comment_docname = %s
	""", webnotes.user.name)

def update_security(args=''):
	import json
	args = json.loads(args)
	webnotes.conn.set_value('Profile', args['user'], 'restrict_ip', args.get('restrict_ip'))
	webnotes.conn.set_value('Profile', args['user'], 'login_after', args.get('login_after'))
	webnotes.conn.set_value('Profile', args['user'], 'login_before', args.get('login_before'))

	if 'new_password' in args:
		if cint(webnotes.conn.get_value('Control Panel',None,'sync_with_gateway')):
			import server_tools.gateway_utils
			res = server_tools.gateway_utils.change_password('', args['new_password'], args['user'], args['sys_admin_pwd'])
			if 'Traceback' not in res['message']:
				webnotes.msgprint(res['message'])
		else:
			webnotes.conn.sql("update tabProfile set password=password(%s) where name=%s", (args['new_password'], args['user']))
	else: webnotes.msgprint('Settings Updated')

welcome_txt = """
## %(company)s

Dear %(first_name)s %(last_name)s

Welcome!

A new account has been created for you, here are your details:

login-id: %(name)s
password: %(password)s

To login to your new ERPNext account, please go to:

%(account_url)s
"""
