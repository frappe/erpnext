# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.utils
import os

def execute():
	base_path = webnotes.utils.get_base_path()
	
	# Remove symlinks from public folder:
	# 	- server.py
	# 	- web.py
	# 	- unsupported.html
	# 	- blank.html
	# 	- rss.xml
	# 	- sitemap.xml
	for file in ("server.py", "web.py", "unsupported.html", "blank.html", "rss.xml", "sitemap.xml"):
		file_path = os.path.join(base_path, "public", file)
		if os.path.exists(file_path):
			os.remove(file_path)
			
	# Remove wn-web files
	# 	- js/wn-web.js
	# 	- css/wn-web.css
	for file_path in (("js", "wn-web.js"), ("css", "wn-web.css")):
		file_path = os.path.join(base_path, "public", *file_path)
		if os.path.exists(file_path):
			os.remove(file_path)
			
	# Remove update app page
	webnotes.delete_doc("Page", "update-manager")
