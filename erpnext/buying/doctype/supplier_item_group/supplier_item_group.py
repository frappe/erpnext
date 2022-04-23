# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class SupplierItemGroup(Document):
	def validate(self):
		exists = frappe.db.exists({
			'doctype': 'Supplier Item Group',
			'supplier': self.supplier,
			'item_group': self.item_group
		})
		if exists:
			frappe.throw(_("Item Group has already been linked to this supplier."))