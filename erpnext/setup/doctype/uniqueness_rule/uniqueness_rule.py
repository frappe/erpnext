# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class UniquenessRule(Document):
	pass

def check_uniqueness(doc, method):
	new_doc = doc.as_dict()
	doctype_in_uniqueness_rule = frappe.db.get_value("Uniqueness Rule",{"doctype_name":new_doc.doctype})
	if doctype_in_uniqueness_rule:
		uniqueness_doc = frappe.get_doc("Uniqueness Rule",{"doctype_name":new_doc.doctype})
		uniqueness_doc_fields = [x.field for x in uniqueness_doc.field_names]

		if method == "before_insert":
			filters = {}
		elif method == "on_update":
			filters = {"name":("!=",new_doc.name)}
		for i in uniqueness_doc_fields:
			filters[i] = new_doc.get(i)
		msg = message(new_doc.doctype,uniqueness_doc_fields)

		with_same_values = frappe.db.get_value(new_doc.doctype,filters=filters)
		if with_same_values:
			frappe.throw(_("{0}").format(msg))

def message(doctype, fields):
	field_label = [fld.label for fld in frappe.get_meta(doctype).fields \
		if fld.fieldname in fields]
	value = "values"
	if len(field_label) == 1:
		value = "value"
		msg = "".join(field_label)
	elif len(field_label) == 2:
		msg = " and ".join(field_label)
	else :
		msg = ", ".join(field_label[0:len(field_label)-1]) + \
		" and "+ field_label[len(field_label)-1]

	return 	_("As per Uniqueness Rule, {0} with same {1} for {2} already exists").format(doctype,value,msg)
