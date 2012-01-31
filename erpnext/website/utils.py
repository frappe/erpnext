import webnotes
from webnotes.model.doc import Document

def make_template(doc, path, convert_fields = ['main_section', 'side_section']):
	"""make template"""
	import os, jinja2
	
	markdown(doc, convert_fields)
	
	# write template
	with open(path, 'r') as f:
		temp = jinja2.Template(f.read())
	
	return temp.render(doc = doc.fields)

def markdown(doc, fields):
	"""convert fields to markdown"""
	import markdown2
	# markdown
	for f in fields:
		doc.fields[f + '_html'] = markdown2.markdown(doc.fields[f] or '', \
			extras=["wiki-tables"])


def page_name(title):
	"""make page name from title, and check that there is no duplicate"""
	import re
	name = re.sub('[~!@#$%^&*()<>,."\']', '', title.lower())
	return '-'.join(name.split()[:4])
	
def add_page(title):
	"""add a custom page with title"""
	name = page_name(title)
	if webnotes.conn.sql("""select name from tabPage where name=%s""", name):
		p = Document('Page', name)
	else:
		p = Document('Page')
		
	p.title = title
	p.name = p.page_name = name
	p.module = 'Website'
	p.standard = 'No'

	return p
	
def add_guest_access_to_page(page):
	"""add Guest in Page Role"""
	if not webnotes.conn.sql("""select parent from `tabPage Role`
		where role='Guest' and parent=%s""", page):
		d = Document('Page Role')
		d.parent = page
		d.role = 'Guest'
		d.save()