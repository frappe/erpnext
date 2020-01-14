# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe import _
from frappe.utils.password import get_decrypted_password
from plaid import Client
from plaid.errors import APIError, ItemError

import frappe
import requests

class PlaidConnector():
	def __init__(self, access_token=None):

		plaid_settings = frappe.get_single("Plaid Settings")

		self.config = {
			"plaid_client_id": plaid_settings.plaid_client_id,
			"plaid_secret": get_decrypted_password("Plaid Settings", "Plaid Settings", 'plaid_secret'),
			"plaid_public_key": plaid_settings.plaid_public_key,
			"plaid_env": plaid_settings.plaid_env
		}

		self.client = Client(client_id=self.config.get("plaid_client_id"),
			secret=self.config.get("plaid_secret"),
			public_key=self.config.get("plaid_public_key"),
			environment=self.config.get("plaid_env")
			)

		self.access_token = access_token

	def get_access_token(self, public_token):
		if public_token is None:
			frappe.log_error(_("Public token is missing for this bank"), _("Plaid public token error"))

		response = self.client.Item.public_token.exchange(public_token)
		access_token = response['access_token']

		return access_token

	def auth(self):
		try:
			self.client.Auth.get(self.access_token)
			print("Authentication successful.....")
		except ItemError as e:
			if e.code == 'ITEM_LOGIN_REQUIRED':
				pass
			else:
				pass
		except APIError as e:
			if e.code == 'PLANNED_MAINTENANCE':
				pass
			else:
				pass
		except requests.Timeout:
			pass
		except Exception as e:
			print(e)
			frappe.log_error(frappe.get_traceback(), _("Plaid authentication error"))
			frappe.msgprint({"title": _("Authentication Failed"), "message":e, "raise_exception":1, "indicator":'red'})

	def get_transactions(self, start_date, end_date, account_id=None):
		try:
			self.auth()
			if account_id:
				account_ids = [account_id]

				response = self.client.Transactions.get(self.access_token, start_date=start_date, end_date=end_date, account_ids=account_ids)

			else:
				response = self.client.Transactions.get(self.access_token, start_date=start_date, end_date=end_date)

			transactions = response['transactions']

			while len(transactions) < response['total_transactions']:
				response = self.client.Transactions.get(self.access_token, start_date=start_date, end_date=end_date, offset=len(transactions))
				transactions.extend(response['transactions'])
			return transactions
		except Exception:
			frappe.log_error(frappe.get_traceback(), _("Plaid transactions sync error"))
