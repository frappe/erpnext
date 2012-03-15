# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
	
	import webnotes.defs
	from webnotes.utils import cint
	if hasattr(webnotes.defs, 'sync_with_gateway') and \
			cint(webnotes.defs.sync_with_gateway) or 0:	
		import server_tools.gateway_utils
		webnotes.msgprint(server_tools.gateway_utils.change_password(arg['old_password'], arg['new_password'])['message'])

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
	from webnotes.utils.file_manager import add_file_list, remove_file
	user = webnotes.session['user']
	
	# remove old file
	old_image = webnotes.conn.get_value('Profile', user, 'user_image')
	if old_image:
		remove_file('Profile', user, old_image)
		
	# add new file
	add_file_list('Profile', user, fname, fid)
	webnotes.conn.set_value('Profile', user, 'user_image', fid)

@webnotes.whitelist()	
def set_user_background(fid, fname):
	"""
		Set uploaded image as user image
	"""
	from webnotes.utils.file_manager import add_file_list, remove_file
	user = webnotes.session['user']
	
	# remove old file
	old_image = webnotes.conn.get_value('Profile', user, 'background_image')
	if old_image:
		remove_file('Profile', user, old_image)
		
	# add new file
	add_file_list('Profile', user, fname, fid)
	webnotes.conn.set_value('Profile', user, 'background_image', fid)
