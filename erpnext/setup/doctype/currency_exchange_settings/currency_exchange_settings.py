# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class CurrencyExchangeSettings(Document):
	def validate(self):
		if len(self.req_params) != 3:
			frappe.throw(_("Make sure all the three mandatory parameters are filled."))
		req_params = {
			'transaction_date': '2021-08-01',
			'from_currency': 'USD',
			'to_currency': 'INR'
		}
		params = {}
		for row in self.req_params:
			try:
				params[row.key] = req_params[row.value]
				req_params.pop(row.value)
			except:
				frappe.throw(_("Make sure all the three mandatory parameters are filled."))
		import requests
		api_url = self.api_endpoint
		try:
			response = requests.get(api_url, params=params)
		except requests.exceptions.RequestException as e:
			frappe.throw("Error: " + str(e))
		response.raise_for_status()
		value = response.json()
		try:
			rate = value[str(self.result_key)]
		except KeyError:
			frappe.throw(_("Invalid result key."))
		if not isinstance(rate, (int, float)):
			frappe.throw(_("Returned exchange rate is neither integer not float."))
		frappe.msgprint(_("Exchange rate of USD to INR on 01-08-2021 is ") + str(rate))
