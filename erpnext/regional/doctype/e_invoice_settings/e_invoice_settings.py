# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

class EInvoiceSettings(Document):
	def validate(self):
		if self.enable and not self.credentials:
			frappe.throw(_('You must add atleast one credentials to be able to use E Invoicing.'))

