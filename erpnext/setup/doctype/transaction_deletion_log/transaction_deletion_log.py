# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.utils import cint
import frappe
from frappe.model.document import Document

class TransactionDeletionLog(Document):
	def on_submit(self):
		doctypes = frappe.get_all('Doctype',
			filters={
				'issingle' : 0,
				'istable' : 0
			})

		for doctype in doctypes:
			if doctype.name != 'Transaction Deletion Log':
				doctype_fields = frappe.get_meta(doctype.name).as_dict()['fields']
				for doctype_field in doctype_fields:
					if doctype_field['fieldtype'] == 'Link' and doctype_field['options'] == 'Company':
						no_of_docs = frappe.db.count(doctype.name, {
							doctype_field['fieldname'] : self.company
						})
						if no_of_docs > 0:
							# populate DocTypes table
							self.append('doctypes', {
								"doctype_name" : doctype.name,
								"no_of_docs" : no_of_docs
							})

							# delete the docs linked with the specified company
							frappe.db.delete(doctype.name, {
								doctype_field['fieldname'] : self.company
							})

							naming_series = frappe.db.get_value('DocType', doctype.name, 'autoname')
							if naming_series:
								if '#' in naming_series:
									self.update_naming_series(naming_series, doctype.name)
						break

	def update_naming_series(self, naming_series, doctype_name):
		if '.' in naming_series:
			prefix, hashes = naming_series.rsplit(".", 1)
		else:
			prefix, hashes = naming_series.rsplit("{", 1)
		last = frappe.db.sql("""select max(name) from `tab{0}`
						where name like %s""".format(doctype_name), prefix + "%")
		if last and last[0][0]:
			last = cint(last[0][0].replace(prefix, ""))
		else:
			last = 0

		frappe.db.sql("""update tabSeries set current = %s where name=%s""", (last, prefix))