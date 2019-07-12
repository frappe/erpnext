# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class GoogleMaps(Document):

	def validate(self):
		if not frappe.db.get_single_value("Google Settings", "enable"):
			frappe.throw(_("Enable Google Integration from Google Settings."))
			
		if not frappe.db.get_single_value("Google Settings", "api_key"):
			frappe.throw(_("Enter API Key in Google Settings for Google Maps Integration."))
