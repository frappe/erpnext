# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JournalEntryTemplate(Document):
	pass

@frappe.whitelist()
def get_naming_series():
	return frappe.get_meta("Journal Entry").get_field("naming_series").options
