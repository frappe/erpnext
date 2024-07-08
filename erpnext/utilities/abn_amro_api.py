import requests
import os

class AbnAmroAPI:
	def __init__(self, client_id, cert_path, key_path, api_key, scope, api_url):
		self.client_id = client_id
		self.cert_path = cert_path
		self.key_path = key_path
		self.api_key = api_key
		self.scope = scope
		self.api_url = api_url


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
		cert_path = ('/Users/nkilicarslan/Downloads/CertificateCommercial (1).crt',
					 '/Users/nkilicarslan/Downloads/PrivateKeyCommercial (1).key')
		# Send the POST request
		response = requests.post(self.api_url, headers=headers, data=payload, cert=cert_path)

		# Check the response
		if response.status_code == 200:
			return response.json()['access_token']
		else:
			return None

	# def get_access_token(self):
	#     # Define the curl command
	#     cmd = [
	#         'curl', '-X', 'POST', 'https://auth-mtls-sandbox.abnamro.com/as/token.oauth2',
	#         '-v',
	#         '--cert', '/Users/nkilicarslan/Downloads/CertificateCommercial.crt',
	#         '--key', '/Users/nkilicarslan/Downloads/PrivateKeyCommercial.key',
	#         '-H', 'Cache-Control: no-cache',
	#         '-H', 'Content-Type: application/x-www-form-urlencoded',
	#         '-d',
	#         'grant_type=client_credentials&client_id=test_client&scope=account:details:read account:balance:read account:transaction:read'
	#     ]
	#
	#     # Run the curl command
	#     process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	#     stdout, stderr = process.communicate()
	#
	#     # Parse the output
	#     try:
	#         response = json.loads(stdout)
	#         return response['access_token']
	#     except json.JSONDecodeError:
	#         print("Error decoding JSON:", stdout)
	#         return None
	#     except KeyError:
	#         print("KeyError:", stdout)
	#         return None

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
		
dir = os.path.dirname(__file__)
certificate_path = os.path.join(dir, 'CertificateCommercial.crt')
private_key_path = os.path.join(dir, 'PrivateKeyCommercial.key')




abn_amro_api = AbnAmroAPI('test_client',
						  certificate_path,
						  private_key_path,
						  'PWL3VDT9Y3sXMz1WWjvJTxRBxZgQkSr9',
						  'account:balance:read account:details:read account:transaction:read',
						'https://auth-mtls-sandbox.abnamro.com/as/token.oauth2')

