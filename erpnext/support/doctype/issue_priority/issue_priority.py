# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class IssuePriority(Document):

	def validate(self):
		if frappe.db.exists("Issue Priority", {"name": self.name}):
			frappe.throw(_("Issue Priority Already Exists"))
