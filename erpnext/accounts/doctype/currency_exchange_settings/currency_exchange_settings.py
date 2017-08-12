# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.utils import cint
from frappe import msgprint


class CurrencyExchangeSettings(Document):
	def validate(self):
		self.validate_stale_days()

	def validate_stale_days(self):
		if not self.allow_stale and cint(self.stale_days) <= 0:
			msgprint(
				"Stale Days should start from 1.", title='Error', indicator='red',
				raise_exception=1)

