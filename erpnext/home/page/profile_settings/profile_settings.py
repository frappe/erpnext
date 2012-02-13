import webnotes

from webnotes.utils import load_json, cint, nowdate

@webnotes.whitelist()
def change_password(arg):
	"""
		Change password
	"""
	arg = load_json(arg)
	
	if not webnotes.conn.sql('select name from tabProfile where name=%s and password=password(%s)', (webnotes.session['user'], arg['old_password'])):
		webnotes.msgprint('Old password is not correct', raise_exception=1)
			
	from webnotes.utils import nowdate
	webnotes.conn.sql("update tabProfile set password=password(%s), modified=%s where name=%s",(arg['new_password'], nowdate(), webnotes.session['user']))
	webnotes.msgprint('Password Updated');

@webnotes.whitelist()
def get_user_details(arg=None):
	"""
		Returns user first name, last name and bio
	"""
	return webnotes.conn.sql("select first_name, last_name, bio from tabProfile where name=%s", webnotes.user.name, as_dict=1)[0]
	
@webnotes.whitelist()
def set_user_details(arg=None):
	"""
		updates user details given in argument
	"""
	from webnotes.model.doc import Document
	
	p = Document('Profile', webnotes.user.name)
	arg_dict = load_json(arg)
	if not 'bio' in arg_dict: arg_dict['bio'] = None
	if not 'last_name' in arg_dict: arg_dict['last_name'] = None
	p.fields.update(arg_dict)
	p.save()
	webnotes.msgprint('Updated')

@webnotes.whitelist()
def set_user_image(fid, fname):
	"""
		Set uploaded image as user image
	"""
	from webnotes.utils.file_manager import add_file_list, remove_all
	remove_all('Profile', webnotes.session['user'])
	add_file_list('Profile', webnotes.session['user'], fname, fid)
