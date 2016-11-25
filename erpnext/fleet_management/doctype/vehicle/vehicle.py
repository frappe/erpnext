# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class Vehicle(Document):
	def validate(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Insurance Start date should be less than Insurance End date"))