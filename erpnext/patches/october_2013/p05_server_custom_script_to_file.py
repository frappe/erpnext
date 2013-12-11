# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	"""
		Assuming that some kind of indentation exists:
		- Find indentation of server custom script
		- replace indentation with tabs
		- Add line:
			class CustomDocType(DocType):
		- Add tab indented code after this line
		- Write to file
		- Delete custom script record
	"""
	import os
	from webnotes.utils import get_site_base_path
	from core.doctype.custom_script.custom_script import make_custom_server_script_file
	for name, dt, script in webnotes.conn.sql("""select name, dt, script from `tabCustom Script`
		where script_type='Server'"""):
			if script and script.strip():
				try:
					script = indent_using_tabs(script)
					make_custom_server_script_file(dt, script)
				except IOError, e:
					if "already exists" not in repr(e):
						raise
			
def indent_using_tabs(script):
	for line in script.split("\n"):
		try:
			indentation_used = line[:line.index("def ")]
			script = script.replace(indentation_used, "\t")
			break
		except ValueError:
			pass
	
	return script