# website patch

import webnotes
from webnotes.model.doc import Document

def execute():	
	add_website_manager()
	from webnotes.modules import reload_doc
	from webnotes.model import delete_doc
	
	delete_doc('Website', 'Module Def', 'Website')
	reload_doc('website', 'Module Def', 'Website')
	reload_doc('website', 'Role', 'Website Manager')

	webnotes.conn.sql("""delete from `tabModule Def Role` where parent='Website'""")
	d = Document('Module Def Role')
	d.parent = 'Website'
	d.role = 'Website Manager'
	d.save()
	
	reload_doc('website', 'doctype', 'about_us_settings')
	reload_doc('website', 'doctype', 'about_us_team')
	reload_doc('website', 'doctype', 'blog')
	reload_doc('website', 'doctype', 'blog_subscriber')
	reload_doc('website', 'doctype', 'contact_us_settings')
	reload_doc('website', 'doctype', 'product')
	reload_doc('website', 'doctype', 'product_group')
	reload_doc('website', 'doctype', 'products_settings')
	reload_doc('website', 'doctype', 'related_page')
	reload_doc('website', 'doctype', 'style_settings')
	reload_doc('website', 'doctype', 'top_bar_item')
	reload_doc('website', 'doctype', 'web_page')
	reload_doc('website', 'doctype', 'website_settings')

	reload_doc('website', 'page', 'about')
	reload_doc('website', 'page', 'blog')
	reload_doc('website', 'page', 'contact')
	reload_doc('website', 'page', 'products')
	reload_doc('website', 'page', 'unsubscribe')
		
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
