# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.html_utils import clean_html

class WebPageSection(Document):
	@property
	def column_value(self):
		return cint(12 / cint(self.no_of_columns or 3))

	def validate(self):
		for item in self.items:
			item_doc = frappe.get_doc(item.content_doctype, item.content_document)
			if item.content_doctype == 'Blog Post' and not item_doc.published:
				frappe.throw("Blog Post '{}' not published".format(item_doc.title))
			elif item.content_doctype == 'Item' and not item_doc.show_in_website:
				frappe.throw("Product Item '{}' not shown in website".format(item_doc.item_name))

	def map_to_cards(self):
		"""Map the children in the items table field to card-like objects for rendering"""
		# Adds directly to the object __dict__, see the python SimpleNamespace class for precedent
		for item in self.items:
			item_doc = frappe.get_doc(item.content_doctype, item.content_document)
			if item.content_doctype == 'Blog Post':
				item.__dict__['title']        = item_doc.title
				item.__dict__['subtitle']     = item_doc.blog_category
				item.__dict__['image']        = None
				item.__dict__['content']      = item_doc.blog_intro
				item.__dict__['route']        = item_doc.route
				item.__dict__['route_rel']    = ''
			elif item.content_doctype == 'Item':
				item.__dict__['title']        = item_doc.item_name
				item.__dict__['subtitle']     = item_doc.item_group
				item.__dict__['image']        = item_doc.website_image
				item.__dict__['content']      = clean_html(item_doc.web_long_description) or item_doc.description
				item.__dict__['route']        = item_doc.route
				item.__dict__['route_rel']    = ''
			else:
				item.__dict__.update(item_doc.__dict__)
				rel = [ None if item_doc.route_follow else 'nofollow', 'external' if item_doc.route_external else None ]
				item.__dict__['route_rel'] = ' '.join(filter(None, rel))

		# Hacky way to fix column_value property not available to template
		self.__dict__['column_value'] = self.column_value
		return self
