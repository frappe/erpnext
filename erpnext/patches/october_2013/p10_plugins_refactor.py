# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes, os, shutil

def execute():
	# changed cache key for plugin code files
	for doctype in webnotes.conn.sql_list("""select name from `tabDocType`"""):
		webnotes.cache().delete_value("_server_script:"+doctype)
	
	# move custom script reports to plugins folder
	for name in webnotes.conn.sql_list("""select name from `tabReport`
		where report_type="Script Report" and is_standard="No" """):
			bean = webnotes.bean("Report", name)
			bean.save()
			
			module = webnotes.conn.get_value("DocType", bean.doc.ref_doctype, "module")
			path = webnotes.modules.get_doc_path(module, "Report", name)
			for extn in ["py", "js"]:
				file_path = os.path.join(path, name + "." + extn)
				plugins_file_path = webnotes.plugins.get_path(module, "Report", name, extn=extn)
				if not os.path.exists(plugins_file_path) and os.path.exists(file_path):
					shutil.copyfile(file_path, plugins_file_path)