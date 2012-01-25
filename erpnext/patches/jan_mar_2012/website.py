# website patch

import webnotes
def execute():	
	cleanup_file_data()
	return
	update_patch_log()
	from webnotes.modules import reload_doc
	reload_doc('website', 'Module Def', 'Website')
	reload_doc('website', 'Role', 'Website Manager')
	reload_doc('website', 'doctype', 'home_settings')
	reload_doc('website', 'doctype', 'top_bar_settings')
	reload_doc('website', 'doctype', 'top_bar_item')
	reload_doc('website', 'page', 'home')

def cleanup_file_data():
	webnotes.conn.commit()
	webnotes.conn.sql("""alter table `tabFile Data` drop column blob_content""")
	webnotes.conn.begin()

def update_patch_log():
	webnotes.conn.commit()
	webnotes.conn.sql("""alter table __PatchLog engine=InnoDB""")
	webnotes.conn.begin()
