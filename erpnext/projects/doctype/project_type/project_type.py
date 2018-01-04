# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _

class ProjectType(Document):
	def on_trash(self):
		if self.name == "External":
			frappe.throw(_("You cannot delete Project Type 'External'"))