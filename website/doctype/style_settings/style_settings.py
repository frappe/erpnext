# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		"""make custom css"""
		from jinja2 import Template
		from webnotes.webutils import get_hex_shade
		import os
		
		default_colours = {
			"background_color": "FFFFFF",
			"page_background": "FFFFFF",
			"top_bar_background": "FFFFFF",
			"top_bar_foreground": "444444",
			"page_headings": "222222",
			"page_text": "000000"
		}
		
		for d in default_colours:
			if not self.doc.fields.get(d):
				self.doc.fields[d] = default_colours[d]
		
		self.validate_colors()
		
		with open(os.path.join(
				os.path.dirname(os.path.abspath(__file__)), 
				'custom_template.css'), 'r') as f:
			temp = Template(f.read())
		
		self.prepare()
		
		self.doc.custom_css = temp.render(doc = self.doc, get_hex_shade=get_hex_shade)
		if self.doc.add_css:
			self.doc.custom_css += '\n\n/* User CSS */\n\n' + self.doc.add_css
		
		from webnotes.sessions import clear_cache
		clear_cache('Guest')

		from webnotes.webutils import clear_cache
		clear_cache()
		
		for f in ["small_font_size", "at_import", "heading_text_style"]:
			if f in self.doc.fields:
				del self.doc.fields[f]
	
	def validate_colors(self):
		if (self.doc.page_background or self.doc.page_text) and \
			self.doc.page_background==self.doc.page_text:
				webnotes.msgprint(_("Page text and background is same color. Please change."),
					raise_exception=1)

		if (self.doc.top_bar_background or self.doc.top_bar_foreground) and \
			self.doc.top_bar_background==self.doc.top_bar_foreground:
				webnotes.msgprint(_("Top Bar text and background is same color. Please change."),
					raise_exception=1)

	
	def prepare(self):
		if not self.doc.font_size:
			self.doc.font_size = '13px'
			
		self.doc.small_font_size = cstr(cint(self.doc.font_size[:-2])-2) + 'px'
		self.doc.page_border = cint(self.doc.page_border)
		
		fonts = []
		if self.doc.google_web_font_for_heading:
			fonts.append(self.doc.google_web_font_for_heading)
		if self.doc.google_web_font_for_text:
			fonts.append(self.doc.google_web_font_for_text)
			
		fonts = list(set(fonts))
		
		if self.doc.heading_text_as:
			self.doc.heading_text_style = {
				"UPPERCASE": "uppercase",
				"Title Case":"capitalize",
				"lowercase": "lowercase"
			}.get(self.doc.heading_text_as) or ""
		
		self.doc.at_import = ""
		for f in fonts:
			self.doc.at_import += "\n@import url(https://fonts.googleapis.com/css?family=%s:400,700);" % f.replace(" ", "+")

	
	def on_update(self):
		"""rebuild pages"""
		from website.helpers.make_web_include_files import make
		make()