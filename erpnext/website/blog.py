import webnotes

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
	template_args = { 'comment_list': [comment] }
	
	# get html of comment row
	comment_html = website.web_cache.build_html(template_args, 'html/comment.html')

	return comment_html
	