import webnotes
from webnotes.model.doc import Document
from webnotes.modules import reload_doc

def execute():
	add_default_home_page()
	reload_doc('setup','doctype','manage_account')

	
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
