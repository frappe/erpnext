# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today
from frappe import _

class QualityReview(Document):
	pass

@frappe.whitelist()
def create_review(reference_doctype, reference_name, review):
	doc = frappe.get_doc({
		"doctype": "Quality Review",
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"date": today(),
		"review": review
	}).insert(ignore_permissions=True)
	frappe.msgprint(_("Quality Review {0} Created.".format(doc.name)))
