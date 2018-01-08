# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShareholderParty(Document):
	def validate(self):
		already_exists = None
		docs = frappe.get_all('Shareholder Party')
		for doc in docs:
			if doc.name == self.name: continue
			doc = frappe.get_doc('Shareholder Party', doc.name)
			if len(doc.shareholder_list) == len(self.shareholder_list):
				old_doc = [x.shareholder for x in doc.shareholder_list ]
				new_doc = [x.shareholder for x in self.shareholder_list]
				if set(old_doc) == set(new_doc):
					already_exists = doc.name
					break
		if already_exists:
			frappe.throw('This party type already exists under a different name: {0}'.format(already_exists))
