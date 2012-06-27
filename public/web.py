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
	import webnotes
	try:
		if 'page' in webnotes.form_dict:
			html = get_html(webnotes.form_dict['page'])
		else:
			# show home page
			html = get_html('index')
	except Exception, e:
		html = get_html('404')

	print "Content-Type: text/html"
	print
	print html.encode('utf-8')

def scrub_page_name(page_name):
	if page_name.endswith('.html'):
		page_name = page_name[:-5]
	return page_name

def get_html(page_name):
	import webnotes
	import website.web_cache
	page_name = scrub_page_name(page_name)
	
	if page_name == '404':
		traceback = webnotes.getTraceback()
		
		# script is used to display traceback in error console
		args = {
			'comments': """error: %s""" % traceback,
			'template': '404.html',
		}
		# 	'script': """(function() {
		# 		var error = "ERROR: %s";
		# 		console.log(error);
		# 	})();""" % traceback.replace('"', '\\"').replace('\n', ' \\\n'),
		# }
				
	else:
		args = {
			'comments': """page: %s""" % page_name,
			'template': 'page.html',
		}
	
	html = website.web_cache.load_from_web_cache(page_name, **args)
	
	return html

if __name__=="__main__":
	init()
	respond()
