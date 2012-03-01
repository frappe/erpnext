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

@webnotes.whitelist()
def get_list(arg=None):
	"""get list of messages"""
	webnotes.form_dict['limit_start'] = int(webnotes.form_dict['limit_start'])
	webnotes.form_dict['limit_page_length'] = int(webnotes.form_dict['limit_page_length'])
	webnotes.form_dict['user'] = webnotes.session['user']

	if webnotes.form_dict['contact'] == webnotes.session['user']:
		# set all messages as read
		webnotes.conn.sql("""UPDATE `tabComment Widget Record`
		set docstatus = 1 where comment_doctype in ('My Company', 'Message')
		and comment_docname = %s
		""", webnotes.user.name)
				
		# return messages
		return webnotes.conn.sql("""select * from `tabComment Widget Record` 
		where (owner=%(contact)s or comment_docname=%(user)s)
		and comment_doctype in ('My Company', 'Message')
		order by creation desc
		limit %(limit_start)s, %(limit_page_length)s""", webnotes.form_dict, as_dict=1)		
	else:
		return webnotes.conn.sql("""select * from `tabComment Widget Record` 
		where (owner=%(contact)s and comment_docname=%(user)s)
		or (owner=%(user)s and comment_docname=%(contact)s)
		and comment_doctype in ('My Company', 'Message')
		order by creation desc
		limit %(limit_start)s, %(limit_page_length)s""", webnotes.form_dict, as_dict=1)
		

@webnotes.whitelist()
def get_active_users(arg=None):
	return webnotes.conn.sql("""select name from tabProfile 
		where ifnull(enabled,0)=1 and
		docstatus < 2 and 
		name not in ('Administrator', 'Guest') 
		order by first_name""", as_dict=1)

@webnotes.whitelist()
def post(arg=None):
	"""post message"""
	import json
	arg = json.loads(arg)
	from webnotes.model.doc import Document
	d = Document('Comment Widget Record')
	d.comment = arg['txt']
	d.comment_docname = arg['contact']
	d.comment_doctype = 'Message'
	d.save()
	
@webnotes.whitelist()
def delete(arg=None):
	webnotes.conn.sql("""delete from `tabComment Widget Record` where name=%s""", 
		webnotes.form_dict['name']);
	