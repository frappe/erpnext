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

# html generation functions

template_map = {
	'Web Page': 'html/web_page.html',
	'Blog': 'html/blog_page.html',
	'Item': 'html/product_page.html',
}

def get_html(page_name, comments=''):
	import conf
	
	html = ''
	
	# load from cache, if auto cache clear is falsy
	if not (hasattr(conf, 'auto_cache_clear') and conf.auto_cache_clear or 0):
		html = load_from_cache(page_name)

	if not html:
		html = load_into_cache(page_name)
		comments += "\n\npage load status: fresh"
	
	# insert comments
	import webnotes.utils
	html += """\n<!-- %s -->""" % webnotes.utils.cstr(comments)
	
	return html

def load_from_cache(page_name):
	import webnotes
	
	result = search_cache(page_name)

	if not result:
		if page_name in get_predefined_pages():
			# if a predefined page doesn't exist, load it into cache
			return None
		else:
			# if page doesn't exist, raise exception
			raise Exception, "Page %s not found" % page_name

	return result[0][0]

def load_into_cache(page_name):
	args = prepare_args(page_name)
	
	html = build_html(args)
	
	# create cache entry for predefined pages, if not exists
	if page_name in get_predefined_pages():
		create_cache(page_name)
	
	import webnotes
	webnotes.conn.begin()
	webnotes.conn.set_value('Web Cache', page_name, 'html', html)
	webnotes.conn.commit()
	
	return html

def get_predefined_pages():
	"""
		gets a list of predefined pages
		they do not exist in `tabWeb Page`
	"""
	import os
	import conf
	import website.utils
	
	pages_path = os.path.join(conf.modules_path, 'website', 'templates', 'pages')
	
	page_list = []
	
	for page in os.listdir(pages_path):
		page_list.append(website.utils.scrub_page_name(page))

	return page_list

def prepare_args(page_name):
	import webnotes
	if page_name == 'index':
		page_name = get_home_page()

	if page_name in get_predefined_pages():
		args = {
			'template': 'pages/%s.html' % page_name,
			'name': page_name,
			'webnotes': webnotes
		}
	else:
		args = get_doc_fields(page_name)
	
	args.update(get_outer_env())
	
	return args
	
def get_home_page():
	import webnotes
	doc_name = webnotes.conn.get_value('Website Settings', None, 'home_page')
	if doc_name:
		page_name = webnotes.conn.get_value('Web Page', doc_name, 'page_name')
	else:
		page_name = 'login'

	return page_name

def get_doc_fields(page_name):
	import webnotes
	doc_type, doc_name = webnotes.conn.get_value('Web Cache', page_name, ['doc_type', 'doc_name'])
	
	import webnotes.model.code
	obj = webnotes.model.code.get_obj(doc_type, doc_name)
	
	if hasattr(obj, 'prepare_template_args'):
		obj.prepare_template_args()
		
	args = obj.doc.fields
	args['template'] = template_map[doc_type]
	
	return args

def get_outer_env():
	"""
		env dict for outer template
	"""
	import webnotes
	return {
		'top_bar_items': webnotes.conn.sql("""\
			select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='top_bar_items'
			order by idx asc""", as_dict=1),
	
		'footer_items': webnotes.conn.sql("""\
			select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='footer_items'
			order by idx asc""", as_dict=1),
			
		'brand': webnotes.conn.get_value('Website Settings', None, 'brand_html') or 'ERPNext',
		'copyright': webnotes.conn.get_value('Website Settings', None, 'copyright'),
		'favicon': webnotes.conn.get_value('Website Settings', None, 'favicon')
	}

def build_html(args):
	"""
		build html using jinja2 templates
	"""
	import os
	import conf
	templates_path = os.path.join(conf.modules_path, 'website', 'templates')
	
	from jinja2 import Environment, FileSystemLoader
	jenv = Environment(loader = FileSystemLoader(templates_path))
	html = jenv.get_template(args['template']).render(args)
	return html

# cache management
def search_cache(page_name):
	if not page_name: return ()
	import webnotes
	return webnotes.conn.sql("""\
		select html, doc_type, doc_name
		from `tabWeb Cache`
		where name = %s""", page_name)

def create_cache(page_name, doc_type=None, doc_name=None):
	# check if a record already exists
	result = search_cache(page_name)
	if result: return
	
	# create a Web Cache record
	import webnotes.model.doc
	d = webnotes.model.doc.Document('Web Cache')
	d.name = page_name
	d.doc_type = doc_type
	d.doc_name = doc_name
	d.html = None
	d.save()

def clear_cache(page_name, doc_type=None, doc_name=None):
	"""
		* if no page name, clear whole cache
		* if page_name, doc_type and doc_name match, clear cache's copy
		* else, raise exception that such a page already exists
	"""
	import webnotes

	if not page_name:
		webnotes.conn.sql("""update `tabWeb Cache` set html = ''""")
		return
	
	result = search_cache(page_name)

	if not doc_type or (result and result[0][1] == doc_type and result[0][2] == doc_name):
		webnotes.conn.set_value('Web Cache', page_name, 'html', '')
	else:
		webnotes.msgprint("""Page with name "%s" already exists as a %s.
			Please save it with another name.""" % (page_name, result[0][1]),
			raise_exception=1)

def delete_cache(page_name):
	"""
		delete entry of page_name from Web Cache
		used when:
			* web page is deleted
			* blog is un-published
	"""
	import webnotes
	webnotes.conn.sql("""delete from `tabWeb Cache` where name=%s""", page_name)

def refresh_cache(build=None):
	"""delete and re-create web cache entries"""
	import webnotes
	
	# webnotes.conn.sql("delete from `tabWeb Cache`")
	
	clear_cache(None)
	
	query_map = {
		'Web Page': """select page_name, name from `tabWeb Page` where docstatus=0""",
		'Blog': """\
			select page_name, name from `tabBlog`
			where docstatus = 0 and ifnull(published, 0) = 1""",
		'Item': """\
			select page_name, name from `tabItem`
			where docstatus = 0 and ifnull(show_in_website, 0) = 1""",
	}

	for dt in query_map:
		if build and dt in build: 
			for result in webnotes.conn.sql(query_map[dt], as_dict=1):
				create_cache(result['page_name'], dt, result['name'])
				load_into_cache(result['page_name'])
			
	for page_name in get_predefined_pages():
		create_cache(page_name, None, None)
		if build: load_into_cache(page_name)