import webnotes

sql = webnotes.conn.sql
from webnotes.model.doc import Document

def execute():
	add_default_home_page()

def add_default_home_page():
	d = Document('Default Home Page')
	d.parent = 'Control Panel'
	d.parenttype = 'Control Panel'
	d.parentfield = 'default_home_pages'
	d.role = 'Guest'
	d.home_page = 'Login Page'
	d.save(1)