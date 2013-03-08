# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
import website.utils
from webnotes import _

@webnotes.whitelist(allow_guest=True)
def get_blog_list(start=0, by=None, category=None):
	import webnotes
	condition = ""
	if by:
		condition = " and t1.blogger='%s'" % by.replace("'", "\'")
	if category:
		condition += " and t1.blog_category='%s'" % category.replace("'", "\'")
	query = """\
		select
			t1.title, t1.name, t1.page_name, t1.creation as creation, 
				ifnull(t1.blog_intro, t1.content) as content, 
				t2.full_name, t2.avatar, t1.blogger,
				(select count(name) from `tabComment` where
					comment_doctype='Blog' and comment_docname=t1.name) as comments
		from `tabBlog` t1, `tabBlogger` t2
		where ifnull(t1.published,0)=1
		and t1.blogger = t2.name
		%(condition)s
		order by creation desc, name asc
		limit %(start)s, 5""" % {"start": start, "condition": condition}
		
	result = webnotes.conn.sql(query, as_dict=1)

	# strip html tags from content
	import webnotes.utils
	
	for res in result:
		from webnotes.utils import global_date_format, get_fullname
		res['published'] = global_date_format(res['creation'])
		if not res['content']:
			res['content'] = website.utils.get_html(res['page_name'])
		res['content'] = res['content'][:140]
		if res.avatar and not "/" in res.avatar:
			res.avatar = "files/" + res.avatar
		
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

def get_blog_template_args():
	return {
		"categories": webnotes.conn.sql_list("select name from `tabBlog Category` order by name")
	}
	
def get_writers_args():
	bloggers = webnotes.conn.sql("select * from `tabBlogger` order by full_name", as_dict=1)
	for blogger in bloggers:
		if blogger.avatar and not "/" in blogger.avatar:
			blogger.avatar = "files/" + blogger.avatar
		
	return {
		"bloggers": bloggers,
		"texts": {
			"all_posts_by": _("All posts by")
		},
		"categories": webnotes.conn.sql_list("select name from `tabBlog Category` order by name")
	}