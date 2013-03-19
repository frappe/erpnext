# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

def get_args():
	if not webnotes.form_dict.doctype or not webnotes.form_dict.name \
		or not webnotes.form_dict.format:
		return {
			"body": """<h1>Error</h1>
				<p>Parameters doctype, name and format required</p>
				<pre>%s</pre>""" % repr(webnotes.form_dict)
		}
		
	obj = webnotes.get_obj(webnotes.form_dict.doctype, webnotes.form_dict.name)
	return {
		"body": get_html(obj.doc, obj.doclist)
	}

def get_html(doc, doclist):
	from jinja2 import Environment
	from core.doctype.print_style.print_style import get_print_style
	from core.doctype.print_format.print_format import get_print_format

	template = Environment().from_string(get_print_format(webnotes.form_dict.format))
	
	args = {
		"doc": doc,
		"doclist": doclist,
		"print_style": get_print_style()
	}
	html = template.render(args)
	return html
