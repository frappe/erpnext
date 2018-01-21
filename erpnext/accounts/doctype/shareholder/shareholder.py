# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address

# module imports - 
import json

class Shareholder(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def on_trash(self):
		delete_contact_and_address('Shareholder', self.name)

	def validate(self):
		already_exists = None

		docs = frappe.get_all('Shareholder')
		self.contacts = json.loads( self.contact_list )['contacts']
		for doc in docs:
			# if same doc no need to check
			if doc.name == self.name: continue

			doc = frappe.get_doc('Shareholder', doc.name)
			doc.contacts  = json.loads( doc.contact_list )['contacts']

			# match and check if all linked contacs are the same
			if len(doc.contacts) == len(self.contacts):
				if set(doc.contacts) == set(self.contacts):
					already_exists = doc.title
					break

		if already_exists:
			frappe.throw('The Shareholder/s already exist/s under a different name: {0}'.format(already_exists))
