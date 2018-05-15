# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate

class RetentionBonus(Document):
	def validate(self):
		if frappe.get_value("Employee", self.employee, "status") == "Left":
			frappe.throw(_("Cannot create Retention Bonus for left Employees"))
		if getdate(self.bonus_payment_date) < getdate():
			frappe.throw(_("Bonus Payment Date cannot be a past date"))
