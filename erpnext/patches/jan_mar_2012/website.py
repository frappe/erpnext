# website patch

import webnotes
from webnotes.model.doc import Document

def execute():	
	add_website_manager()
	return
	cleanup_file_data()
	update_patch_log()
	from webnotes.modules import reload_doc
	reload_doc('website', 'Role', 'Website Manager')
	reload_doc('website', 'Module Def', 'Website')
	reload_doc('website', 'doctype', 'home_settings')
	reload_doc('website', 'doctype', 'top_bar_settings')
	reload_doc('website', 'doctype', 'top_bar_item')
	reload_doc('website', 'doctype', 'contact_us_settings')
	reload_doc('website', 'doctype', 'about_us_settings')

	reload_doc('website', 'page', 'home')
	reload_doc('website', 'page', 'contact')
	reload_doc('website', 'page', 'about')
		
def add_website_manager():
	"""add website manager to system manager"""
	for i in webnotes.conn.sql("""select distinct parent from tabUserRole 
		where role='System Manager'"""):
		if not webnotes.conn.sql("""select parent from tabUserRole 
			where role='Website Manager' and parent=%s""", i[0]):
			d = Document('UserRole')
			d.parent = i[0]
			d.role = 'Website Manager'
			d.save(1)

def cleanup_file_data():
	webnotes.conn.commit()
	webnotes.conn.sql("""alter table `tabFile Data` drop column blob_content""")
	webnotes.conn.begin()

def update_patch_log():
	webnotes.conn.commit()
	webnotes.conn.sql("""alter table __PatchLog engine=InnoDB""")
	webnotes.conn.begin()
