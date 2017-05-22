# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now

class FixedAssetCustody(Document):
	
	def before_save(self):
		self.validate_duplicate_custody()

	def validate_duplicate_custody(self):
		
		fa=frappe.db.sql("select item_code, employee from `tabFixed Asset Custody` where item_code ='{0}' and name <> '{1}' and docstatus <> 2".format(self.item_code, self.name))
		if fa:
			frappe.throw(_("This Asset is already a custody with '{0}'".format(fa[0][1])))
	
	def before_update_after_submit(self):
		
		if not getattr(self, "__islocal", None) and frappe.db.exists(self.doctype, self.name):
			self.previous_doc = frappe.db.get_value(self.doctype, self.name, "*", as_dict=True)
		else:
			self.previous_doc = None
		
		if self.previous_doc and self.employee != self.previous_doc.employee:
			child = self.append('fixed_asset_custody_history', {})
			child.old_employee = self.previous_doc.employee
			child.employee = self.employee
			child.date = now()
