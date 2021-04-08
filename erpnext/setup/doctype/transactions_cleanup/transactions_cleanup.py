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
			print("*" * 50)
			doctype_to_be_deleted = frappe.get_doc('DocType', doctype.doctype_name)
			print(doctype_to_be_deleted.autoname)
			prefix, hashes = doctype_to_be_deleted.autoname.rsplit(".", 1)
			print(prefix)
			# print(self.status)
			print(self.docstatus)
		print(self.as_dict())
		
	def on_submit(self):
		for doctype in self.doctypes:
			frappe.db.delete(doctype.doctype_name, {
				'company' : self.company
			})

			doctype_to_be_cleared = frappe.get_doc('DocType', doctype.doctype_name)
			if '#' in doctype_to_be_cleared.autoname:
				self.reset_naming_series(doctype_to_be_cleared)

	def reset_naming_series(self, doctype):
		prefix, hashes = doctype.autoname.rsplit(".", 1)
		frappe.db.sql("UPDATE `tabSeries` SET `current` = 0 WHERE `name`=%s", prefix)