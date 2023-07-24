# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
import plaid
import requests
from frappe import _
from plaid.api import plaid_api


class PlaidConnector:
	def __init__(self, access_token=None):
		self.access_token = access_token
		self.settings = frappe.get_single("Plaid Settings")
		self.products = ["transactions"]
		self.client_name = frappe.local.site
		self.configuration = plaid.Configuration(
			host=self.settings.plaid_env,
			api_key={
				"clientId": self.settings.plaid_client_id,
				"secret": self.settings.get_password("plaid_secret"),
				"plaidVersion": "2020-09-14",
			},
		)
		self.api_client = plaid.ApiClient(self.configuration)
		self.client = plaid_api.PlaidApi(self.api_client)

	def get_access_token(self, public_token):
		if public_token is None:
			frappe.log_error("Plaid: Public token is missing")
		request = plaid_api.ItemPublicTokenExchangeRequest(public_token)
		response = self.client.item_public_token_exchange(request)
		access_token = response["access_token"]
		return access_token

	def get_token_request(self, update_mode=False):
		country_codes = (
			["US", "CA", "FR", "IE", "NL", "ES", "GB"]
			if self.settings.enable_european_access
			else ["US", "CA"]
		)
		args = {
			"client_name": self.client_name,
			# only allow Plaid-supported languages and countries (LAST: Sep-19-2020)
			"language": frappe.local.lang if frappe.local.lang in ["en", "fr", "es", "nl"] else "en",
			"country_codes": [plaid_api.CountryCode(cc) for cc in country_codes],
			"user": plaid_api.LinkTokenCreateRequestUser(
				{"client_user_id": frappe.generate_hash(frappe.session.user, length=32)}
			),
		}

		if update_mode:
			args["access_token"] = self.access_token
		else:
			args.update(
				{
					"client_id": self.settings.plaid_client_id,
					"secret": self.settings.plaid_secret,
					"products": [plaid_api.Products(p) for p in self.products],
				}
			)

		return args

	def get_link_token(self, update_mode=False):
		token_request = self.get_token_request(update_mode)

		try:
			request = plaid_api.LinkTokenCreateRequest(token_request)
			response = self.client.link_token_create(request)
		except plaid.ApiException as e:
			response = json.loads(e.body)
			if response["error_code"] == "ITEM_LOGIN_REQUIRED":
				pass
			elif response["error_code"] == "PLANNED_MAINTENANCE":
				pass
			elif response["error_type"] == "INVALID_REQUEST":
				frappe.log_error("Plaid: Invalid request error")
				frappe.msgprint(_("Please check your Plaid client ID and secret values"))
			else:
				frappe.log_error("Plaid: Authentication error")
				frappe.throw(_(str(e)), title=_("Authentication Failed"))
		else:
			return response["link_token"]

	def auth(self):
		try:
			request = plaid_api.AuthGetRequest(self.access_token)
			self.client.auth_get(request)
		except plaid.ApiException as e:
			response = json.loads(e.body)
			if response["error_code"] == "ITEM_LOGIN_REQUIRED":
				pass
			elif response["error_code"] == "PLANNED_MAINTENANCE":
				pass
			else:
				frappe.log_error("Plaid: Authentication error")
				frappe.throw(_(str(e)), title=_("Authentication Failed"))
		except requests.Timeout:
			pass

	def get_transactions(self, start_date, end_date, account_id=None):
		self.auth()
		kwargs = dict(access_token=self.access_token, start_date=start_date, end_date=end_date)
		if account_id:
			kwargs.update(
				dict(
					options=plaid_api.TransactionsGetRequestOptions(
						account_ids=[account_id],
					)
				)
			)

		try:
			request = plaid_api.TransactionsGetRequest(**kwargs)
			response = self.client.transactions_get(request)
			transactions = response["transactions"]
			while len(transactions) < response["total_transactions"]:
				request = plaid_api.TransactionsGetRequest(
					self.access_token,
					start_date=start_date,
					end_date=end_date,
					options=plaid_api.TransactionsGetRequestOptions(
						offset=len(transactions),
					),
				)
				response = self.client.transactions_get(request)
				transactions.extend(response["transactions"])
			return transactions
		except plaid.ApiException as e:
			response = json.loads(e.body)
			if response["error_code"] == "ITEM_LOGIN_REQUIRED":
				raise response
			else:
				frappe.log_error("Plaid: Transactions sync error")
