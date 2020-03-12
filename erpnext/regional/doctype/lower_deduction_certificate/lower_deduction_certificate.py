# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class LowerDeductionCertificate(Document):
	def validate(self):
		if getdate(self.valid_upto) < getdate(self.valid_from):
			frappe.throw(_("Valid Upto date cannot be before Valid From date"))
