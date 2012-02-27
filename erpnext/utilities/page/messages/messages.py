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
		where enabled=1 and
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
	