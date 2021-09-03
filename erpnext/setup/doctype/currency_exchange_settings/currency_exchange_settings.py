# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class CurrencyExchangeSettings(Document):
	def validate(self):
		if len(self.req_params) > 3:
			frappe.throw(_("Make sure no mandatory parameters are repeated."))
		transaction_date = '2021-08-01'
		from_currency = 'USD'
		to_currency = 'INR'
		req_params = {
			"transaction_date": transaction_date,
			"from_currency": from_currency,
			"to_currency": to_currency
		}
		params = {}
		for row in self.req_params:
			try:
				params[row.key] = req_params[row.value]
				req_params.pop(row.value)
			except:
				frappe.throw(_("Make sure no mandatory parameters are repeated."))
		for eparam in self.extra_params:
			params[eparam.key] = eparam.value.format(
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
		except KeyError:
			frappe.throw("Invalid result key. Response: " + response.text)
		if not isinstance(value, (int, float)):
			frappe.throw(_("Returned exchange rate is neither integer not float."))
		self.url = response.url
		frappe.msgprint("Exchange rate of USD to INR on 01-08-2021 is " + str(value))
