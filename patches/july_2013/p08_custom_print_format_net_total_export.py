# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import re

def execute():
	for name, html in webnotes.conn.sql("""select name, html from `tabPrint Format` where standard='No'
		and ifnull(html, '')!=''"""):
			changed = False
			for match in re.findall("(doc.net_total.*doc.conversion_rate)", html):
				if match.replace(" ", "") == "doc.net_total/doc.conversion_rate":
					html = html.replace(match, "doc.net_total_export")
					changed = True
		
			if changed:
				webnotes.conn.set_value("Print Format", name, "html", html)
			