# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class PaymentEntryDeduction(Document):
	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		self.key = value
