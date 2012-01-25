def make_template(doc, path, convert_fields = ['main_section', 'side_section']):
	"""make template"""
	import os, jinja2, markdown2
	
	# markdown
	for f in convert_fields:
		doc.fields[f + '_html'] = markdown2.markdown(doc.fields[f] or '', \
			extras=["wiki-tables"])
	
	# write template
	with open(path, 'r') as f:
		temp = jinja2.Template(f.read())
	
	return temp.render(doc = doc.fields)	