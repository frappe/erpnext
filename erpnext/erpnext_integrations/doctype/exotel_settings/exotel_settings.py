# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import requests
import frappe
from frappe import _

class ExotelSettings(Document):
	def validate(self):
		self.verify_credentials()

	def verify_credentials(self):
		if self.enabled:
			response = requests.get('https://api.exotel.com/v1/Accounts/{sid}'
				.format(sid = self.account_sid), auth=(self.api_key, self.api_token))
			if response.status_code != 200:
				frappe.throw(_("Invalid credentials"))