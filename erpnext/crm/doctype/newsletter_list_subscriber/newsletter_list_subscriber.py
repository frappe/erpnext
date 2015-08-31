# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class NewsletterListSubscriber(Document):
	pass

def after_doctype_insert():
	frappe.db.add_unique("Newsletter List Subscriber", ("newsletter_list", "email"))
