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

from __future__ import unicode_literals
import webnotes

from webnotes.utils import load_json, cint, nowdate


def check_demo():
	demo_user = 'demo@erpnext.com'
	if webnotes.session['user']==demo_user:
		webnotes.msgprint("Can't change in demo", raise_exception=1)
	

@webnotes.whitelist()
def change_password(arg):
	"""
		Change password
	"""
	check_demo()
	arg = load_json(arg)
	
	if not webnotes.conn.sql("""select * from `__Auth` where `user`=%s
			and password=password(%s)""",
			(webnotes.session["user"], arg["old_password"])):
		webnotes.msgprint('Old password is not correct', raise_exception=1)

	webnotes.conn.sql("""update `__Auth` set password=password(%s)
		where `user`=%s""", (arg["new_password"], webnotes.session["user"]))

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
	check_demo()
	from webnotes.model.doc import Document
	
	p = Document('Profile', webnotes.user.name)
	arg_dict = load_json(arg)
	if not 'bio' in arg_dict: arg_dict['bio'] = None
	if not 'last_name' in arg_dict: arg_dict['last_name'] = None
	if not 'email_signature' in arg_dict: arg_dict['email_signature'] = None
	p.fields.update(arg_dict)
	p.save()
	webnotes.msgprint('Updated')

@webnotes.whitelist()
def set_user_image():
	"""
		Set uploaded image as user image
	"""
	check_demo()
	from webnotes.utils.file_manager import add_file_list, remove_file, save_uploaded
	user = webnotes.session['user']

	fid, fname = save_uploaded()
		
	# remove old file
	old_image = webnotes.conn.get_value('Profile', user, 'user_image')
	if old_image:
		remove_file('Profile', user, old_image)
		
	# add new file
	add_file_list('Profile', user, fname, fid)
	webnotes.conn.set_value('Profile', user, 'user_image', fid)
	
	return fid

@webnotes.whitelist()	
def set_user_background():
	"""
		Set uploaded image as user image
	"""
	check_demo()
	from webnotes.utils.file_manager import add_file_list, remove_file, save_uploaded
	user = webnotes.session['user']

	fid, fname = save_uploaded()
	
	# remove old file
	old_image = webnotes.conn.get_value('Profile', user, 'background_image')
	if old_image:
		remove_file('Profile', user, old_image)
		
	# add new file
	add_file_list('Profile', user, fname, fid)
	webnotes.conn.set_value('Profile', user, 'background_image', fid)
	
	return fid

@webnotes.whitelist()	
def set_user_theme():
	webnotes.conn.set_default("theme", webnotes.form_dict.theme, webnotes.session.user)
