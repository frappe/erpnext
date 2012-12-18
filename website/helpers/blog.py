# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
import website.utils

@webnotes.whitelist(allow_guest=True)
def get_blog_list(args=None):
	"""
		args = {
			'start': 0,
		}
	"""
	import webnotes
	
	if not args: args = webnotes.form_dict
	
	query = """\
		select
			name, page_name, content, owner, creation as creation,
			title, (select count(name) from `tabComment` where
				comment_doctype='Blog' and comment_docname=`tabBlog`.name) as comments
		from `tabBlog`
		where ifnull(published,0)=1
		order by creation desc, name asc
		limit %s, 5""" % args.start
		
	result = webnotes.conn.sql(query, args, as_dict=1)

	# strip html tags from content
	import webnotes.utils
	
	for res in result:
		from webnotes.utils import global_date_format, get_fullname
		res['full_name'] = get_fullname(res['owner'])
		res['published'] = global_date_format(res['creation'])
		if not res['content']:
			res['content'] = website.utils.get_html(res['page_name'])
		res['content'] = split_blog_content(res['content'])

	return result

@webnotes.whitelist(allow_guest=True)
def add_comment(args=None):
	"""
		args = {
			'comment': '',
			'comment_by': '',
			'comment_by_fullname': '',
			'comment_doctype': '',
			'comment_docname': '',
			'page_name': '',
		}
	"""
	import webnotes
	import webnotes.utils, markdown2
	import webnotes.widgets.form.comments	
	
	if not args: args = webnotes.form_dict
	args['comment'] = unicode(markdown2.markdown(args.get('comment') or ''))
	
	comment = webnotes.widgets.form.comments.add_comment(args)
	
	# since comments are embedded in the page, clear the web cache
	website.utils.clear_cache(args.get('page_name'))
	
	comment['comment_date'] = webnotes.utils.global_date_format(comment['creation'])
	template_args = { 'comment_list': [comment], 'template': 'html/comment.html' }
	
	# get html of comment row
	comment_html = website.utils.build_html(template_args)
	
	# notify commentors 
	commentors = [d[0] for d in webnotes.conn.sql("""select comment_by from tabComment where
		comment_doctype='Blog' and comment_docname=%s and
		ifnull(unsubscribed, 0)=0""", args.get('comment_docname'))]
	
	blog = webnotes.conn.sql("""select * from tabBlog where name=%s""", 
		args.get('comment_docname'), as_dict=1)[0]
	
	from webnotes.utils.email_lib.bulk import send
	send(recipients=list(set(commentors + [blog['owner']])), 
		doctype='Comment', 
		email_field='comment_by', 
		subject='New Comment on Blog: ' + blog['title'], 
		message='%(comment)s<p>By %(comment_by_fullname)s</p>' % args)
	
	return comment_html

@webnotes.whitelist(allow_guest=True)
def add_subscriber():
	"""add blog subscriber to lead"""
	full_name = webnotes.form_dict.get('your_name')
	email = webnotes.form_dict.get('your_email_address')
	name = webnotes.conn.sql("""select name from tabLead where email_id=%s""", email)
	
	from webnotes.model.doc import Document
	if name:
		lead = Document('Lead', name[0][0])
	else:
		lead = Document('Lead')
	
	if not lead.source: lead.source = 'Blog'
	lead.unsubscribed = 0
	lead.blog_subscriber = 1
	lead.lead_name = full_name
	lead.email_id = email
	lead.save()
		
def get_blog_content(blog_page_name):
	import website.utils
	content = website.utils.get_html(blog_page_name)
	content = split_blog_content(content)
	import webnotes.utils
	content = webnotes.utils.escape_html(content)
	return content
	
def split_blog_content(content):
	content = content.split("<!-- begin blog content -->")
	content = len(content) > 1 and content[1] or content[0]
	content = content.split("<!-- end blog content -->")
	content = content[0]
	return content