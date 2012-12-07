# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

def make():
	import os
	import webnotes
	import website.utils
	import startup.event_handlers

	if not webnotes.conn:
		webnotes.connect()
	
	home_page = website.utils.get_home_page()

	fname = 'js/wn-web.js'
	if os.path.basename(os.path.abspath('.'))!='public':
		fname = os.path.join('public', fname)
			
	if hasattr(startup.event_handlers, 'get_web_script'):
		with open(fname, 'w') as f:
			script = 'window.home_page = "%s";\n' % home_page
			script += startup.event_handlers.get_web_script()
			f.write(script)

	fname = 'css/wn-web.css'
	if os.path.basename(os.path.abspath('.'))!='public':
		fname = os.path.join('public', fname)

	# style - wn.css
	if hasattr(startup.event_handlers, 'get_web_style'):
		with open(fname, 'w') as f:
			f.write(startup.event_handlers.get_web_style())