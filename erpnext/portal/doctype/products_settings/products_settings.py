# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document

class ProductsSettings(Document):
	def validate(self):
		if self.home_page_is_products:
			website_settings = frappe.get_doc('Website Settings')
			website_settings.home_page = 'products'
			website_settings.save()

def home_page_is_products(doc, method):
	'''Called on saving Website Settings'''
	if doc.home_page != 'products':
		frappe.db.set_value('Products Settings', None, 'home_page_is_products', 0)
	else:
		frappe.db.set_value('Products Settings', None, 'home_page_is_products', 1)


