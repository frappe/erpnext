import webnotes
import website.utils

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def autoname(self):
		"""name from title"""
		self.doc.name = website.utils.page_name(self.doc.title)

	def validate(self):
		"""make page for this product"""					
		p = website.utils.add_page(self.doc.title)
		
		from jinja2 import Template
		import os
	
		website.utils.markdown(self.doc, ['main_section', 'side_section'])
		
		self.add_page_links()
		
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)

		p.save()
		
		website.utils.add_guest_access_to_page(p.name)
		self.cleanup_temp()
			
	def add_page_links(self):
		"""add links for next_page and see_also"""
		if self.doc.next_page:
			self.doc.next_page_html = """<div class="info-box round">
			<p style="text-align: right"><b>Next:</b>
				<a href="#!%(name)s">%(title)s</a></p></div>""" % {"name":self.doc.next_page, \
						"title": webnotes.conn.get_value("Page", self.doc.next_page, "title")}

		self.doc.see_also = ''
		for l in webnotes.conn.sql("""select distinct t1.page, t2.title from
			`tabRelated Page` t1, tabPage t2 where
			t1.page = t2.name order by t2.title""", as_dict=1):
			self.doc.see_also += """<p><a href="#!%(page)s">%(title)s</a></p>""" % l
		
	def cleanup_temp(self):
		"""cleanup temp fields"""
		fl = ['main_section_html', 'side_section_html', 'see_also', 'next_page_html']
		for f in fl:
			if f in self.doc.fields:
				del self.doc.fields[f]
	