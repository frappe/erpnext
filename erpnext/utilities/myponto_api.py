import base64
import os
import requests

class MyPontoAPI:
	def __init__(self, base_url, client_id=None, client_secret=None):
		self.client_id = client_id or os.getenv('MYPONTO_CLIENT_ID')
		self.client_secret = client_secret or os.getenv('MYPONTO_CLIENT_SECRET')
		self.encoded_secret = self.encode_credentials()
		self.base_url = base_url

	def encode_credentials(self):
		credentials = f"{self.client_id}:{self.client_secret}"
		encoded_credentials = base64.b64encode(credentials.encode()).decode()
		return encoded_credentials

	def get_access_token(self):
		url = self.base_url + '/oauth2/token'
		headers = {
			"Content-Type": "application/x-www-form-urlencoded",
			"Accept": "application/json",
			"Authorization": f"Basic {self.encoded_secret}"
		}
		data = {
			"grant_type": "client_credentials"
		}
		response = requests.post(url, headers=headers, data=data, verify=False)
		if response.status_code == 200:
			return response.json()['access_token']
		else:
			return None

	def get_list_of_accounts(self, access_token):
		url = self.base_url + '/accounts'
		headers = {
			"Accept": "application/json",
			"Authorization": f"Bearer {access_token}"
		}
		params = {
			"limit": 100
		}
		response = requests.get(url, headers=headers, params=params, verify=False)
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_list_of_transactions(self, access_token, account_id):
		url = self.base_url + f'/accounts/{account_id}/transactions'
		headers = {
			"Accept": "application/json",
			"Authorization": f"Bearer {access_token}"
		}
		params = {
			"limit": 100
		}
		response = requests.get(url, headers=headers, params=params, verify=False)
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_transaction_details(self, access_token, account_id, transaction_id):
		url = self.base_url + f'/accounts/{account_id}/transactions/{transaction_id}'
		headers = {
			"Accept": "application/json",
			"Authorization": f"Bearer {access_token}"
		}
		response = requests.get(url, headers=headers, verify=False)
		if response.status_code == 200:
			return response.json()
		else:
			return None


myponto_api = MyPontoAPI(base_url='https://api.myponto.com')
