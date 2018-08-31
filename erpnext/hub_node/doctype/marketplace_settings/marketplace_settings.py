# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, time

from frappe.model.document import Document
from frappe.utils import add_years, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.utilities.product import get_price, get_qty_in_stock
from six import string_types

class MarketplaceSettings(Document):

	def validate(self):
		self.site_name = frappe.utils.get_url()


	def get_marketplace_url(self):
		return self.marketplace_url


	def register(self):
		""" Create a User on hub.erpnext.org and return username/password """
		self.site_name = frappe.utils.get_url()

		register_url = self.get_marketplace_url() + '/api/method/hub.hub.api.register'
		data = {'profile': self.as_json(), 'email': frappe.session.user}
		headers = {'accept': 'application/json'}

		response = requests.post(register_url, data = data, headers = headers)
		response.raise_for_status()
		if response.ok:
			message = response.json().get('message')
		else:
			frappe.throw(json.loads(response.text))

		return message or None


	def unregister(self):
		""" Disable the User on hub.erpnext.org"""
		pass
