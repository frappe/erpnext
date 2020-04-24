# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on

class JournalEntryTemplate(Document):
	def autoname(self):
		self.name = self.voucher_type + ' - ' + frappe.get_value('Company', self.company, 'abbr')

