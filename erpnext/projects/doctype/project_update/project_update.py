# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ProjectUpdate(Document):
	pass

@frappe.whitelist()
def current_day_time(doc,method):
	doc.date = frappe.utils.today()
	doc.time = frappe.utils.now_datetime().strftime('%H:%M:%S')
