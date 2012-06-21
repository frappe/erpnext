#!/usr/bin/env python

"""
return a dynamic page from website templates

all html pages except login-page.html get generated here
"""

import cgi, cgitb, os, sys
cgitb.enable()

# import libs
sys.path.append('..')
import conf
sys.path.append('../lib/py')
sys.path.append(conf.modules_path)

def init():
	import webnotes
	webnotes.form = cgi.FieldStorage(keep_blank_values=True)
	for key in webnotes.form.keys():
		webnotes.form_dict[key] = webnotes.form.getvalue(key)
	webnotes.connect()

def respond():
	html = get_html()
	print "Content-Type: text/html"
	print
	print html.encode('utf-8')

def get_html():
	import webnotes
	from webnotes.model.doc import Document
	# Get web page
	outer_env_dict = get_outer_env()
	try:
		if 'page' in webnotes.form_dict:
			page_name = webnotes.form_dict['page']
			if page_name.endswith('.html'):
				page_name = page_name[:-5]
				
			if page_name.startswith('blog'):
				raise Exception
				#page_name = 
			else:
				page_name = get_web_page_name(page_name)		
		else:
			from webnotes.cms import get_home_page
			page_name = get_home_page('Guest')
		
		page = Document('Web Page', page_name)
		page.fields.update(outer_env_dict)

		return build_html(page.fields, "page: %s" % page_name)
		
	except Exception, e:
		return build_html(outer_env_dict, "error: %s" % webnotes.getTraceback(), '404.html')

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

def build_html(args, comments, template='page.html'):
	"""build html using jinja2 templates"""
	from webnotes.utils import cstr
	from jinja2 import Environment, FileSystemLoader
	jenv = Environment(loader = FileSystemLoader('../erpnext/website/templates'))
	
	html = jenv.get_template(template).render(args)
	html += "\n<!-- %s -->" % cstr(comments)
	return html

def get_web_page_name(page_name):
	"""get page by shortname"""
	import webnotes
	return webnotes.conn.sql("""select name from `tabWeb Page` where page_name=%s""", page_name)[0][0]

		
if __name__=="__main__":
	init()
	respond()
