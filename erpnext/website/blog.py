import webnotes

@webnotes.whitelist(allow_guest=True)
def get_blog_list(args=None):
	"""
		args = {
			'limit_start': 0,
			'limit_page_length': 10,
		}
	"""
	import webnotes
	
	if not args: args = webnotes.form_dict
	
	query = """\
		select
			cache.name as name, cache.html as content,
			blog.owner as owner, blog.creation as published,
			blog.title as title
		from `tabWeb Cache` cache, `tabBlog` blog
		where cache.doc_type = 'Blog' and blog.page_name = cache.name
		order by published desc, name asc"""
	
	from webnotes.widgets.query_builder import add_limit_to_query
	query, args = add_limit_to_query(query, args)
	
	result = webnotes.conn.sql(query, args, as_dict=1)

	# strip html tags from content
	import webnotes.utils
	import website.web_cache
	
	for res in result:
		from webnotes.utils import global_date_format, get_fullname
		res['full_name'] = get_fullname(res['owner'])
		res['published'] = global_date_format(res['published'])
		res['content'] = split_blog_content(res['content'])
		res['content'] = res['content'][:1000]

	return result

@webnotes.whitelist(allow_guest=True)
def get_recent_blog_list(args=None):
	"""
		args = {
			'limit_start': 0,
			'limit_page_length': 5,
			'name': '',
		}
	"""
	import webnotes
	
	if not args: args = webnotes.form_dict
	
	query = """\
		select name, title, left(content, 100) as content
		from tabBlog
		where ifnull(published,0)=1 and
		name!=%(name)s order by creation desc"""
	
	from webnotes.widgets.query_builder import add_limit_to_query
	query, args = add_limit_to_query(query, args)
	
	result = webnotes.conn.sql(query, args, as_dict=1)

	# strip html tags from content
	import webnotes.utils
	for res in result:
		res['content'] = webnotes.utils.strip_html(res['content'])

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
	
	if not args: args = webnotes.form_dict
	
	import webnotes.widgets.form.comments
	comment = webnotes.widgets.form.comments.add_comment(args)
	
	# since comments are embedded in the page, clear the web cache
	import website.web_cache
	website.web_cache.clear_cache(args.get('page_name'),
		args.get('comment_doctype'), args.get('comment_docname'))
	
	import webnotes.utils
	
	comment['comment_date'] = webnotes.utils.pretty_date(comment['creation'])
	template_args = { 'comment_list': [comment], 'template': 'html/comment.html' }
	
	# get html of comment row
	comment_html = website.web_cache.build_html(template_args)

	return comment_html

def get_content(blog_page_name):
	import website.web_cache
	content = website.web_cache.get_html(blog_page_name)
	
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