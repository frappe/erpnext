# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import json
import requests
from six.moves.urllib.parse import urlencode

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_url, call_hook_method, cint, flt, cstr
from frappe.integrations.utils import create_request_log, create_payment_gateway
from frappe.utils import get_request_site_address
from frappe.utils.password import get_decrypted_password
from erpnext.erpnext_integrations.utils import create_mode_of_payment
from erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_connector import MpesaConnector
from erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_custom_fields import create_custom_pos_fields

class MpesaSettings(Document):
	supported_currencies = ["KSh"]

	def validate(self):
		create_payment_gateway('Mpesa-' + self.payment_gateway_name, settings='Mpesa Settings', controller=self.payment_gateway_name)
		create_mode_of_payment('Mpesa-' + self.payment_gateway_name)
		call_hook_method('payment_gateway_enabled', gateway='Mpesa-' + self.payment_gateway_name)

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Mpesa does not support transactions in currency '{0}'").format(currency))

	def on_update(self):
		create_custom_pos_fields()