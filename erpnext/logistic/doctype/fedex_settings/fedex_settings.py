# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.logistic.utils import create_shipper

class FedExSettings(Document):
	def validate_credentials(self):
		pass

	def on_upate(self):
		create_shipper("Fedex")
