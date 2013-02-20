# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

import os
import webnotes
import website.utils

def make():

	if not webnotes.conn:
		webnotes.connect()
	
	home_page = website.utils.get_home_page()

	fname = 'js/wn-web.js'
	if os.path.basename(os.path.abspath('.'))!='public':
		fname = os.path.join('public', fname)
			
	with open(fname, 'w') as f:
		f.write(get_web_script())

	fname = 'css/wn-web.css'
	if os.path.basename(os.path.abspath('.'))!='public':
		fname = os.path.join('public', fname)

	# style - wn.css
	with open(fname, 'w') as f:
		f.write(get_web_style())

def get_web_script():
	"""returns web startup script"""
	user_script = ""
	
	ws = webnotes.doc("Website Settings", "Website Settings")

	if ws.google_analytics_id:
		user_script += google_analytics_template % ws.google_analytics_id
	
	user_script += (webnotes.conn.get_value('Website Script', None, 'javascript') or '')

	return user_script
	
def get_web_style():
	"""returns web css"""
	return webnotes.conn.get_value('Style Settings', None, 'custom_css') or ''

google_analytics_template = """

// Google Analytics template

window._gaq = window._gaq || [];
window._gaq.push(['_setAccount', '%s']);
window._gaq.push(['_trackPageview']);

(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();
"""