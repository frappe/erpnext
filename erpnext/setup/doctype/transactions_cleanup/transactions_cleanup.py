# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TransactionsCleanup(Document):
	def before_save(self):
		print("*" * 50)
		print(self.company) # prints name of the company
		for doctype in self.doctypes:
			print(doctype.doctype_name) # prints name of the doctype to be deleted
			print(frappe.get_all(doctype.doctype_name)) # prints the docs to be deleted 
			# doctype_to_be_deleted = doctype.doctype_name
			# print(doctype_to_be_deleted)
		print(self.as_dict())
		
	def on_submit(self):
		for doctype in self.doctypes:
			frappe.db.delete(doctype.doctype_name, {
				'company' : self.company
			})