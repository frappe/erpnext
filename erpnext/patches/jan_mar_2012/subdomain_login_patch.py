import webnotes
from webnotes.model.doc import Document

def execute():
	add_default_home_page()
	cleanup()
	
def cleanup():
	from webnotes.model import delete_doc
	delete_doc("DocType", "SSO Control")
	delete_doc("DocType", "WN ERP Cient Control")
	
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