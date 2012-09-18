from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("delete from `tabProperty Setter` where property in ('width', 'previous_field')")

	webnotes.conn.sql("delete from `tabSingles` where field = 'footer_font_color' and doctype = 'Style Settings'")
