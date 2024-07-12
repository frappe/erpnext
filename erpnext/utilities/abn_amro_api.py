import requests
import os

class AbnAmroAPI:
	def __init__(self, client_id, cert_path, key_path, api_key, scope, payment_scope, api_url, base64_sct_file_data):
		self.client_id = client_id
		self.cert_path = cert_path
		self.key_path = key_path
		self.api_key = api_key
		self.scope = scope
		self.api_url = api_url
		self.payment_scope = payment_scope
		self.base64_sct_file_data = base64_sct_file_data


	def get_headers(self, access_token):
		return {
			'User-Agent': 'PostmanRuntime/7.39.0',
			'Accept': '*/*',
			'Accept-Encoding': 'gzip, deflate, br',
			'Connection': 'keep-alive',
			'Authorization': f'Bearer {access_token}',
			'API-Key': self.api_key
		}

	def get_access_token(self):
		# Define the headers
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
			'User-Agent': 'PostmanRuntime/7.39.0',
			'Accept': '*/*',
			'Accept-Encoding': 'gzip, deflate, br',
			'Connection': 'keep-alive',
			'cache-control': 'no-cache',
		}

		# Define the payload
		payload = {
			'client_id': self.client_id,
			'scope': self.scope,
			'grant_type': 'client_credentials'
		}

		# Define the path to the certificates
		cert_path = (self.cert_path,
					 self.key_path)
		# Send the POST request
		response = requests.post(self.api_url, headers=headers, data=payload, cert=cert_path)

		# Check the response
		if response.status_code == 200:
			return response.json()['access_token']
		else:
			return None

	def get_access_payment_token(self):
		# Define the headers
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
			'cache-control': 'no-cache',
		}

		# Define the payload
		payload = {
			'client_id': self.client_id,
			'scope': self.payment_scope,
			'grant_type': 'client_credentials'
		}

		# Define the path to the certificates
		cert_path = (self.cert_path,
					 self.key_path)
		# Send the POST request
		response = requests.post('https://auth-mtls-sandbox.abnamro.com/as/token.oauth2', headers=headers, data=payload, cert=cert_path)

		# Check the response
		if response.status_code == 200:
			return response.json()['access_token']
		else:
			return None

	def get_account_details(self, account_id, access_token):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/details'

		# Send the GET request
		response = requests.get(url, headers=headers)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_account_balance(self, account_id, access_token):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/balances'

		# Send the GET request
		response = requests.get(url, headers=headers)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_first_set_of_transactions(self, account_id, access_token):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/transactions'

		# Send the GET request
		response = requests.get(url, headers=headers)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_next_set_of_transactions(self, account_id, access_token, next_page_key):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/transactions'

		# Define the query parameters
		params = {'nextPageKey': next_page_key}

		# Send the GET request
		response = requests.get(url, headers=headers, params=params)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_todays_first_set_of_transactions(self, account_id, access_token, datetime):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/transactions'

		# Define the query parameters
		params = {'bookDateFrom': datetime}

		# Send the GET request
		response = requests.get(url, headers=headers, params=params)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_next_set_of_todays_transactions(self, account_id, access_token, datetime, next_page_key):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/transactions'

		# Define the query parameters
		params = {'bookDateFrom': datetime, 'nextPageKey': next_page_key}

		# Send the GET request
		response = requests.get(url, headers=headers, params=params)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_first_set_of_detailtransactions(self, account_id, access_token, bulk_transaction_id):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/batch-transactions/{bulk_transaction_id}'

		# Send the GET request
		response = requests.get(url, headers=headers)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def get_next_set_of_detailtransactions(self, account_id, access_token, bulk_transaction_id,
										   next_page_key):
		# Define the headers
		headers = self.get_headers(access_token)

		# Define the URL
		url = f'https://api-sandbox.abnamro.com/v1/accounts/{account_id}/batch-transactions/{bulk_transaction_id}'

		# Define the query parameters
		params = {'nextPageKey': next_page_key}

		# Send the GET request
		response = requests.get(url, headers=headers, params=params)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None

	def initiate_payment(self, access_token, x_request_id):
		# Define the headers
		headers = {
			'Accept': 'application/json',
			'Authorization': f'Bearer {access_token}',
			'X-Request-ID': x_request_id,
			'Content-Type': 'application/json',
			'API-Key': 'tZSKde7sgfjB0A9GD72cBrLi2dvAoX8D'
		}

		# Define the URL
		url = 'https://api-sandbox.abnamro.com/v1/customer-api/payments'

		# define the payload
		payload = {
			'fileName': 'SampleSCT.xml.lz',
			'fileData': self.base64_sct_file_data
		}

		# Send the POST request
		response = requests.post(url, headers=headers, json=payload)

		# Check the response
		if response.status_code == 200:
			return response.json()
		else:
			return None


dir = os.path.dirname(__file__)
certificate_path = os.path.join(dir, 'CertificateCommercial.crt')
private_key_path = os.path.join(dir, 'PrivateKeyCommercial.key')

test_x_request_id = 'bc69c490-9524-413f-971a-21f1aecd9fe5'

abn_amro_api = AbnAmroAPI('test_client',
						  certificate_path,
						  private_key_path,
						  'PWL3VDT9Y3sXMz1WWjvJTxRBxZgQkSr9',
						  'account:balance:read account:details:read account:transaction:read',
						  'payment:unsigned:write payment:status:read',
						  'https://auth-mtls-sandbox.abnamro.com/as/token.oauth2',
						  'H4sICFchkWYAA1NhbXBsZVNDVC5YTUwAtVXLjtowFN1X6j9E2ZOHgQGi4FEI0NICgyBU3SFIDEQihjrmMf363jgw0MSe6aaRILHPvee+bff5kuy0E2FpvKdt3TYsXSM03Ecx3bT1edCvNPVn/PmT292Hx4RQroE8Tdv6kVEnTvdOyiPxRpaFkMNJuHUuaeQcljE1LMvOf1U9VwMobutbzg+OaZ7PZ+NcNfZsY4Kybf4cDWfhliTLSkxTvqQh0cGwBo/rpzxhfsQDth7QmNPrvsC+sMPXiD3siN1RuhlE2Moe2zXzVUHEZ6TLgwQjy25VrHoF2YHdcOrIQQ3XvIEFnfHqZR1cUgyct88iK2e72THBtoEsoLmuCkJZEJsJf8XuOMHfd0vK6XKZAGdJ0nwTfQjZLMXsThI+oOuidr4Loc/8YNELFqNg8e1IyQKB/29YWWfEIxxM+0Im+/4/SQDy4FB2WmCzUzg87SRITg8B9SYeMBd9y9Mj1RbRyAy6U/Ir6l1CTrv8oRlc83G/oNJd8WLL5alJcJesYk6OTFpNiZ7g8sKwaENgpfLckY43xuPhE/I6Y68FT7Nm1xotaJgMkGWlXGpTYTp3aSP1qB/TAYwnVXvWGfg4c2o8RFCibCXzRslz9apk3fW3bNNheDbs/YDK54uiiDgigouiq7KWV7rdo1Gwhz+QeKG/icbImjA48GLiaDaq1upPrvkgI4tJxe96iSyXAsqSEAGu+eFrW+/Np/p1am6A1JJiH+JX1E3AH9ZOSP1L/XIv3uXLplPZRRmkooWxgdM3Ug3RnVuZAfkwCfzDgbLvA9V4qqOqcqByP94LXTHTU9lR/ZfEPOUswlOyNrLjCK7PJvRevikzJiUUPkiG4Xbw365WU3K3wgheb3tY/AE1BZs6IggAAA==')
