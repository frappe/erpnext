# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document

class CurrencyExchangeSettings(Document):
	def validate(self):
		transaction_date = nowdate()
		from_currency = 'USD'
		to_currency = 'INR'
		params = {}
		for row in self.req_params:
			params[row.key] = row.value.format(
				transaction_date=transaction_date,
				to_currency=to_currency,
				from_currency=from_currency
			)
		import requests
		api_url = self.api_endpoint.format(
			transaction_date=transaction_date,
			to_currency=to_currency,
			from_currency=from_currency
		)
		try:
			response = requests.get(api_url, params=params)
		except requests.exceptions.RequestException as e:
			frappe.throw("Error: " + str(e))
		response.raise_for_status()
		value = response.json()
		try:
			for key in self.result_key:
				value = value[str(key.key).format(
					transaction_date=transaction_date,
					to_currency=to_currency,
					from_currency=from_currency
				)]
		except Exception:
			frappe.throw("Invalid result key. Response: " + response.text)
		if not isinstance(value, (int, float)):
			frappe.throw(_("Returned exchange rate is neither integer not float."))
		self.url = response.url
		frappe.msgprint("Exchange rate of USD to INR is " + str(value))
