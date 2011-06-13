import webnotes

from webnotes.utils import load_json, cint, nowdate

#
# change profile (remote)
#
def change_password(arg):
	arg = load_json(arg)
	
	if cint(webnotes.conn.get_value('Control Panel',None,'sync_with_gateway')):
		import server_tools.server_tools.gateway_utils
		webnotes.msgprint(server_tools.server_tools.gateway_utils.change_password(arg['old_password'], arg['new_password'])['message'])
	else:
		if not webnotes.conn.sql('select name from tabProfile where name=%s and password=password(%s)', (webnotes.session['user'], arg['old_password'])):
			webnotes.msgprint('Old password is not correct', raise_exception=1)
			
		from webnotes.utils import nowdate
		webnotes.conn.sql("update tabProfile set password=password(%s), password_last_updated=%s where name=%s",(arg['new_password'], nowdate(), webnotes.session['user']))
		webnotes.msgprint('Password Updated');

def get_user_details(arg=None):
	"Returns user first name, last name and bio"
	
	return webnotes.conn.sql("select first_name, last_name, bio from tabProfile where name=%s", webnotes.user.name, as_dict=1)[0]
	
def set_user_details(arg=None):
	"updates user details given in argument"
	from webnotes.model.doc import Document
	
	p = Document('Profile', webnotes.user.name)
	p.fields.update(load_json(arg))
	p.save()
	webnotes.msgprint('Updated')
