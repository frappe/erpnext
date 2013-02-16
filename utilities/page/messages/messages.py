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

@webnotes.whitelist()
def get_list(arg=None):
	"""get list of messages"""
	webnotes.form_dict['limit_start'] = int(webnotes.form_dict['limit_start'])
	webnotes.form_dict['limit_page_length'] = int(webnotes.form_dict['limit_page_length'])
	webnotes.form_dict['user'] = webnotes.session['user']

	# set all messages as read
	webnotes.conn.begin()
	webnotes.conn.sql("""UPDATE `tabComment`
	set docstatus = 1 where comment_doctype in ('My Company', 'Message')
	and comment_docname = %s
	""", webnotes.user.name)
	webnotes.conn.commit()

	if webnotes.form_dict['contact'] == webnotes.session['user']:
		# return messages
		return webnotes.conn.sql("""select * from `tabComment` 
		where (owner=%(contact)s 
			or comment_docname=%(user)s 
			or (owner=comment_docname and ifnull(parenttype, "")!="Assignment"))
		and comment_doctype ='Message'
		order by creation desc
		limit %(limit_start)s, %(limit_page_length)s""", webnotes.form_dict, as_dict=1)		
	else:
		return webnotes.conn.sql("""select * from `tabComment` 
		where (owner=%(contact)s and comment_docname=%(user)s)
		or (owner=%(user)s and comment_docname=%(contact)s)
		or (owner=%(contact)s and comment_docname=%(contact)s)
		and comment_doctype ='Message'
		order by creation desc
		limit %(limit_start)s, %(limit_page_length)s""", webnotes.form_dict, as_dict=1)
		

@webnotes.whitelist()
def get_active_users(arg=None):
	return webnotes.conn.sql("""select name,
		(select count(*) from tabSessions where user=tabProfile.name
			and timediff(now(), lastupdate) < time("01:00:00")) as has_session
	 	from tabProfile 
		where ifnull(enabled,0)=1 and
		docstatus < 2 and 
		name not in ('Administrator', 'Guest') 
		order by first_name""", as_dict=1)

@webnotes.whitelist()
def post(arg=None):
	import webnotes
	"""post message"""
	if not arg:
		arg = {}
		arg.update(webnotes.form_dict)
	
	if isinstance(arg, basestring):
		import json
		arg = json.loads(arg)

	from webnotes.model.doc import Document
	d = Document('Comment')
	d.parenttype = arg.get("parenttype")
	d.comment = arg['txt']
	d.comment_docname = arg['contact']
	d.comment_doctype = 'Message'
	d.save()

	import webnotes.utils
	if webnotes.utils.cint(arg.get('notify')):
		notify(arg)
	
@webnotes.whitelist()
def delete(arg=None):
	webnotes.conn.sql("""delete from `tabComment` where name=%s""", 
		webnotes.form_dict['name']);

def notify(arg=None):
	from webnotes.utils import cstr, get_fullname
	from startup import get_url
	
	fn = get_fullname(webnotes.user.name) or webnotes.user.name
	
	url = get_url()
	
	message = '''You have a message from <b>%s</b>:
	
	%s
	
	To answer, please login to your erpnext account at \
	<a href=\"%s\" target='_blank'>%s</a>
	''' % (fn, arg['txt'], url, url)
	
	sender = webnotes.conn.get_value("Profile", webnotes.user.name, "email") \
		or webnotes.user.name
	recipient = [webnotes.conn.get_value("Profile", arg["contact"], "email") \
		or arg["contact"]]
	
	from webnotes.utils.email_lib import sendmail
	sendmail(recipient, sender, message, arg.get("subject") or "You have a message from %s" % (fn,))
	