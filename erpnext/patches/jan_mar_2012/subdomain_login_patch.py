import webnotes
from webnotes.model.doc import Document
from webnotes.modules import reload_doc

def execute():
	add_default_home_page()
	reload_doc('setup','doctype','manage_account')
	webnotes.conn.commit()
	webnotes.conn.sql("drop table if exists tabDocTrigger")
	cleanup()
	
def cleanup():
	webnotes.conn.begin()
	from webnotes.model import delete_doc
	delete_doc("DocType", "SSO Control")
	delete_doc("DocType", "WN ERP Client Control")
	delete_doc("DocType", "Production Tips Common")
	delete_doc("DocType", "DocTrigger")

	# cleanup control panel
	delete_doc("DocType", "Control Panel")
	reload_doc("core", "doctype", "control_panel")

	# cleanup page
	delete_doc("DocType", "Page")
	reload_doc("core", "doctype", "page")
	
	webnotes.conn.sql("""delete from tabSingles
		where field like 'startup_%' and doctype='Control Panel'""")
	
def add_default_home_page():
	if not webnotes.conn.sql("""select name from `tabDefault Home Page`
		where role='Guest' and home_page='Login Page'"""):
		d = Document('Default Home Page')
		d.parent = 'Control Panel'
		d.parenttype = 'Control Panel'
		d.parentfield = 'default_home_pages'
		d.role = 'Guest'
		d.home_page = 'Login Page'
		d.save(1)
