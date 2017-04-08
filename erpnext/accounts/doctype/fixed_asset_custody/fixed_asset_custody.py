# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class FixedAssetCustody(Document):
	
	def before_save(self):
		self.validate_duplicate_custody()

	def validate_duplicate_custody(self):
		fa=frappe.db.sql("select item_code, employee from `tabFixed Asset Custody` where item_code ='{0}' and name <> '{1}' and docstatus <> 2".format(self.item_code, self.name))
		if fa:
			frappe.throw(_("This Asset is already a custody with '{0}'".format(fa[0][1])))