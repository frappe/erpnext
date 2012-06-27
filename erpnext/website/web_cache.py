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

# used by web.py
def load_from_web_cache(page_name, comments, template): #, script=None):
	"""
		* search for page in cache
		* if html exists, return
		* if not, build html, store it in cache, return
	"""
	import webnotes
	import conf
	
	if page_name == 'index':
		page_name = get_index_page()[0]

	res = webnotes.conn.sql("""\
		select html, doc_type, doc_name from `tabWeb Cache`
		where name = %s""", page_name)
	
	# if page doesn't exist, raise exception
	if not res and page_name not in ['404', 'index', 'blog', 'products']:
		raise Exception, "Page %s not found" % page_name
	
	html, doc_type, doc_name = res and res[0] or (None, None, None)
	auto_cache_clear = hasattr(conf, 'auto_cache_clear') and conf.auto_cache_clear or 0
	if not html or auto_cache_clear:
		comments += "\n\npage load status: fresh"
		html = load_into_web_cache(page_name, template, doc_type, doc_name)
	else:
		comments += "\n\npage load status: cached"

	from webnotes.utils import cstr
	html += """\n<!-- %s -->""" % cstr(comments)
	
	# show error in error console
	# if script: html += """\n\n<script>\n%s\n</script>""" % cstr(script)
	return html

def load_into_web_cache(page_name, template, doc_type, doc_name):
	"""build html and store it in web cache"""
	import webnotes
	outer_env_dict = get_outer_env()
	
	if page_name in ['404', 'blog', 'products']:
		args = outer_env_dict
		args.update({
			'name': page_name,
		})
	else:
		if page_name == 'index':
			page_name, doc_type, doc_name = get_index_page()

		from webnotes.model.code import get_obj
		obj = get_obj(doc_type, doc_name)
		if hasattr(obj, 'get_html'):
			obj.get_html()
		args = obj.doc.fields
		args.update(outer_env_dict)
	
	# decide template and update args
	if doc_type == 'Blog':
		template = 'blog/blog.html'
		args.update({ 'insert_code': 1 })
	elif doc_type == 'Item':
		template = 'product/product.html'
		args.update({ 'insert_code': 1 })
	elif doc_type == 'Web Page':
		template = 'web_page.html'
	elif page_name == 'blog':
		template = 'blog/blog_list.html'
		args.update({ 'insert_code': 1 })
	elif page_name == 'products':
		template = 'product/product_list.html'
		args.update({ 'insert_code': 1 })
	
	html = build_html(args, template)
	
	# save html in web cache
	webnotes.conn.begin()
	webnotes.conn.set_value('Web Cache', page_name, 'html', html)
	webnotes.conn.commit()
	
	return html

def build_html(args, template):
	"""build html using jinja2 templates"""
	from jinja2 import Environment, FileSystemLoader
	jenv = Environment(loader = FileSystemLoader('../erpnext/website/templates'))
	html = jenv.get_template(template).render(args)
	return html

def get_outer_env():
	"""env dict for outer template"""
	import webnotes
	return {
		'top_bar_items': webnotes.conn.sql("""select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='top_bar_items'
			order by idx asc""", as_dict=1),
	
		'footer_items': webnotes.conn.sql("""select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='footer_items'
			order by idx asc""", as_dict=1),
			
		'brand': webnotes.conn.get_value('Website Settings', None, 'brand_html'),
		'copyright': webnotes.conn.get_value('Website Settings', None, 'copyright'),
	}

def get_index_page():
	import webnotes
	doc_type = 'Web Page'
	doc_name = webnotes.conn.get_value('Website Settings', None, 'home_page')
	page_name = webnotes.conn.get_value(doc_type, doc_name, 'page_name')
	return page_name, doc_type, doc_name

# cache management
def clear_web_cache(doc_type, doc_name, page_name):
	"""
		* check if a record corresponding to (type, name) exists
		* if exists, just clear html column
		* if does not exist, create a record for (type, name)
		* if a record like (some other type, name) exists, raise exception that the page name is not unique
	"""
	import webnotes
	res = webnotes.conn.get_value('Web Cache', page_name, 'doc_type')
	if not res:
		import webnotes.model.doc
		d = webnotes.model.doc.Document('Web Cache')
		d.name = page_name
		d.doc_type = doc_type
		d.doc_name = doc_name
		d.html = None
		d.save()
	elif res == doc_type:
		webnotes.conn.set_value('Web Cache', page_name, 'html', None)
	else:
		webnotes.msgprint("""Page with name "%s" already exists as a %s.
			Please save it with another name.""" % (page_name, res), raise_exception=1)
		
def clear_all_web_cache():
	import webnotes
	webnotes.conn.sql("update `tabWeb Cache` set html = NULL")
		
def delete_web_cache(page_name):
	"""
		delete entry of page_name from Web Cache
		used when:
			* web page is deleted
			* blog is un-published
	"""
	import webnotes
	webnotes.conn.sql("""\
		delete from `tabWeb Cache`
		where name=%s""", page_name)
		
def build_web_cache():
	"""build web cache so that pages can load faster"""
	pass