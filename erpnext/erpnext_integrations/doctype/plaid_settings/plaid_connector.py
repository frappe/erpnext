# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from plaid.api import plaid_api
from plaid.exceptions import ApiException

PLAID_ENV_URLS = {
	"sandbox": "https://sandbox.plaid.com",
	"development": "https://development.plaid.com",
	"production": "https://production.plaid.com",
}


class PlaidConnector:
	def __init__(self, access_token=None):
		self.access_token = access_token
		self.settings = frappe.get_single("Plaid Settings")
		self.products = ["transactions"]
		self.client_name = frappe.local.site
		self.client = self.get_client()

	def get_client(self):
		from plaid import ApiClient
		from plaid.configuration import Configuration

		config = Configuration(
			host=PLAID_ENV_URLS.get(self.settings.plaid_env),
			api_key={
				"clientId": self.settings.plaid_client_id,
				"secret": self.settings.get_password("plaid_secret"),
			},
		)
		client = ApiClient(config)
		return plaid_api.PlaidApi(client)

	def get_access_token(self, public_token):
		from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest

		if public_token is None:
			frappe.log_error("Plaid: Public token is missing")

		request = ItemPublicTokenExchangeRequest(public_token=public_token)

		try:
			response = self.client.item_public_token_exchange(request)
			return response.access_token
		except ApiException as e:
			frappe.log_error("Plaid Token Exchange Error", e)
			frappe.msgprint(_("Failed to exchange public token Check Error Log for more details"))

	def get_token_request(self, update_mode=False):
		from plaid.model.country_code import CountryCode
		from plaid.model.link_token_create_request import LinkTokenCreateRequest
		from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
		from plaid.model.products import Products

		country_codes = (
			[
				CountryCode("US"),
				CountryCode("CA"),
				CountryCode("FR"),
				CountryCode("IE"),
				CountryCode("NL"),
				CountryCode("ES"),
				CountryCode("GB"),
			]
			if self.settings.enable_european_access
			else [CountryCode("US"), CountryCode("CA")]
		)

		user = LinkTokenCreateRequestUser(client_user_id=frappe.generate_hash(frappe.session.user, length=32))
		request = LinkTokenCreateRequest(
			user=user,
			client_name=self.client_name,
			language=frappe.local.lang if frappe.local.lang in ["en", "fr", "es", "nl"] else "en",
			country_codes=country_codes,
			products=[Products("transactions")] if not update_mode else None,
		)

		if update_mode:
			request.access_token = self.access_token

		return request

	def get_link_token(self, update_mode=False):
		token_request = self.get_token_request(update_mode)

		try:
			response = self.client.link_token_create(token_request)
			return response.link_token
		except ApiException as e:
			frappe.log_error("Plaid API Exception Error", e)
			frappe.msgprint(_("Plaid request Failed Check Error Log for more details."))
		except Exception as e:
			frappe.log_error("Plaid Link Token Error", e)
			frappe.msgprint(_("Failed to generate Plaid Link Token Check Error Log for more details"))

	def get_transactions(self, start_date, end_date, account_id=None):
		from plaid.model.transactions_get_request import TransactionsGetRequest
		from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

		len_trans = 0

		def get_request_data(offset=None):
			kwargs = TransactionsGetRequestOptions()
			if account_id:
				kwargs.account_ids = [account_id]
			if offset:
				kwargs.offset = offset

			return TransactionsGetRequest(
				access_token=self.access_token,
				start_date=getdate(start_date),
				end_date=getdate(end_date),
				options=kwargs,
			)

		try:
			request = get_request_data()
			response = self.client.transactions_get(request)
			transactions = response.transactions
			len_trans += len(transactions)
			while len(transactions) < response.total_transactions:
				request = get_request_data(offset=len(transactions))
				next_response = self.client.transactions_get(request)
				transactions.extend(next_response.transactions)
			return transactions
		except ApiException as e:
			frappe.log_error("Plaid Transactions Error", e)

	def get_bank_details(self, access_token, account_id=None):
		from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest

		request = AccountsBalanceGetRequest(access_token=access_token)
		try:
			result = self.client.accounts_balance_get(request)

			accounts_map = frappe._dict()

			for acc in result.get("accounts", []):
				if account_id and acc["account_id"] == account_id:
					return acc
				accounts_map[acc["account_id"]] = acc
			return accounts_map
		except Exception as e:
			frappe.log_error("Plaid Account Balance Error", e)
			frappe.msgprint(_("Failed to fetch account balace from plaid Check Error Log for more details"))
