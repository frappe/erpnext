# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document


class PaymentTermsTemplateDetail(Document):
	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		self.key = value
