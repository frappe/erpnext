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
		if not self.doc.name:				
			self.doc.name = website.utils.page_name(self.doc.title)

		p = website.utils.add_page(self.doc.name)
		
		from jinja2 import Template
		from webnotes.utils import global_date_format
		import os
	
		self.doc.updated = global_date_format(self.doc.modified)
		website.utils.markdown(self.doc, ['head_section','main_section', 'side_section'])
		
		self.add_page_links()
		
		with open(os.path.join(os.path.dirname(__file__), 'template.html'), 'r') as f:
			p.content = Template(f.read()).render(doc=self.doc)

		p.save()
		
		website.utils.add_guest_access_to_page(p.name)
		self.cleanup_temp()
		self.if_home_clear_cache()
			
	def add_page_links(self):
		"""add links for next_page and see_also"""
		if self.doc.next_page:
			self.doc.next_page_html = """<div class="info-box round" style="text-align: right">
				<b>Next:</b>
				<a href="#!%(name)s">%(title)s</a></div>""" % {"name":self.doc.next_page, \
						"title": webnotes.conn.get_value("Page", self.doc.next_page, "title")}

		self.doc.see_also = ''
		for d in self.doclist:
			if d.doctype=='Related Page':
				tmp = {"page":d.page, "title":webnotes.conn.get_value('Page', d.page, 'title')}
				self.doc.see_also += """<div><a href="#!%(page)s">%(title)s</a></div>""" % tmp
				
	def cleanup_temp(self):
		"""cleanup temp fields"""
		fl = ['main_section_html', 'side_section_html', 'see_also', \
			'next_page_html', 'head_section_html', 'updated']
		for f in fl:
			if f in self.doc.fields:
				del self.doc.fields[f]
				
	def if_home_clear_cache(self):
		"""if home page, clear cache"""
		if webnotes.conn.get_value("Website Settings", None, "home_page")==self.doc.name:
			from webnotes.session_cache import clear_cache
			clear_cache('Guest')			
	