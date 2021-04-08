# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import cint
import frappe
from frappe.model.document import Document

class TransactionsCleanup(Document):
	def before_save(self):
		print("*" * 50)
		print(self.name)
		print(self.company) # prints name of the company
		for doctype in self.doctypes:
			print(doctype.as_dict())

		# 	print(doctype.doctype_name) # prints name of the doctype to be deleted
		# 	print(frappe.get_all(doctype.doctype_name)) # prints the docs to be deleted 
		# 	# doctype_to_be_deleted = doctype.doctype_name
		# 	# print(doctype_to_be_deleted)
		# 	print("*" * 50)
		# 	doctype_to_be_deleted = frappe.get_doc('DocType', doctype.doctype_name)
		# 	print(doctype_to_be_deleted.autoname)
		# 	prefix, hashes = doctype_to_be_deleted.autoname.rsplit(".", 1)
		# 	print(prefix)
		# 	# print(self.status)
		# 	print(self.docstatus)
		# print(self.as_dict())

		# doctypes = frappe.get_all('Doctype',
		# 	filters={
		# 		'issingle' : 0,
		# 		'istable' : 0
		# 	})
		
		# linked_doctypes = []
		# for doctype in doctypes:
		# 	doctype_obj = frappe.get_doc('DocType', doctype.name)
		# 	doctype_dict = doctype_obj.as_dict()
		# 	doctype_fields = doctype_dict['fields']
		# 	for doctype_field in doctype_fields:
		# 		if doctype_field['fieldname'] == "company":
		# 			linked_doctypes.append({
		# 				"doctype" : "Transactions Cleanup Doctype",
		# 				"doctype_name" : doctype.doctype_name,
		# 				"parent" : self.name,
		# 				"parenttype" : "Transactions Cleanup"
		# 				})
		# 			# linked_doctype = frappe.get_doc({
		# 			# 	"doctype" : "Transactions Cleanup Doctype",
		# 			# 	"doctype_name" : doctype.doctype_name,
		# 			# 	"parent" : self.name,
		# 			# 	"parenttype" : "Transactions Cleanup"
		# 			# })
		# 			# linked_doctype.insert()
		# 			break
		# new_doc = frappe.get_doc({
		# 	"doctype" : "Transactions Cleanup",
		# 	"company" : self.company,
		# 	"doctypes" : linked_doctypes
 		# })
		# new_doc.insert()
		
	def on_submit(self):
		for doctype in self.doctypes:
			frappe.db.delete(doctype.doctype_name, {
				'company' : self.company
			})

			doctype_to_be_cleared = frappe.get_doc('DocType', doctype.doctype_name)
			if '#' in doctype_to_be_cleared.autoname:
				self.update_naming_series(doctype_to_be_cleared)

	def update_naming_series(self, doctype):
		prefix, hashes = doctype.autoname.rsplit(".", 1)
		last = frappe.db.sql("""select max(name) from `tab{0}`
						where name like %s""".format(doctype.name), prefix + "%")
		if last and last[0][0]:
			last = cint(last[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.sql("""update tabSeries set current = %s where name=%s""", (last, prefix))