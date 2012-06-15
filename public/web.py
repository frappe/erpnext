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

def get_outer_env():
	"""env for outer (cache this)"""
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
	
def get_page_by_short_name(page_name):
	"""get page by shortname"""
	import webnotes
	return webnotes.conn.sql("""select name from `tabWeb Page` where page_name=%s""", page_name)[0][0]
	
def get_html():
	import webnotes
	from jinja2 import Environment, FileSystemLoader
	from webnotes.model.doc import Document
	
	jenv = Environment(loader = FileSystemLoader('../erpnext/website/templates'))
	
	webnotes.form = cgi.FieldStorage(keep_blank_values=True)
	for key in webnotes.form.keys():
		webnotes.form_dict[key] = webnotes.form.getvalue(key)
	webnotes.connect()

	if 'page' in webnotes.form_dict:
		page_name = webnotes.form_dict['page']
		if page_name.endswith('.html'):
			page_name = page_name[:-5]
		
		#try:
		page_name = get_page_by_short_name(page_name)
		page = Document('Web Page', page_name)
		page.fields.update(get_outer_env())
		return jenv.get_template('page.html').render(page.fields)
		#except Exception, e:
		#	return jenv.get_template('404.html').render(get_outer_env())
	else:
		return jenv.get_template('404.html').render(get_outer_env())
		
if __name__=="__main__":
	print "Content-Type: text/html"
	print
	print get_html().encode('utf-8')
