# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _

class SampleCollection(Document):
	def validate(self):
		if flt(self.sample_qty) <= 0:
			frappe.throw(_('Sample Quantity cannot be negative or 0'), title=_('Invalid Quantity'))
