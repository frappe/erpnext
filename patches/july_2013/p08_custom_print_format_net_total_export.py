from __future__ import unicode_literals
import webnotes
import re

def execute():
	for name, html in webnotes.conn.sql("""select name, html from `tabPrint Format` where standard='No'"""):
		changed = False
		for match in re.findall("(doc.net_total.*doc.conversion_rate)", html):
			if match.replace(" ", "") == "doc.net_total/doc.conversion_rate":
				html = html.replace(match, "doc.net_total_export")
				changed = True
		
		if changed:
			webnotes.conn.set_value("Print Format", name, "html", html)
			