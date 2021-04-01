import base64
import requests
from requests.auth import HTTPBasicAuth
import datetime

class MpesaConnector():
	def __init__(self, env="sandbox", app_key=None, app_secret=None, sandbox_url="https://sandbox.safaricom.co.ke",
		live_url="https://api.safaricom.co.ke"):
		"""Setup configuration for Mpesa connector and generate new access token."""
		self.env = env
		self.app_key = app_key
		self.app_secret = app_secret
		if env == "sandbox":
			self.base_url = sandbox_url
		else:
			self.base_url = live_url
		self.authenticate()

	def authenticate(self):
		"""
		This method is used to fetch the access token required by Mpesa.

		Returns:
			access_token (str): This token is to be used with the Bearer header for further API calls to Mpesa.
		"""
		authenticate_uri = "/oauth/v1/generate?grant_type=client_credentials"
		authenticate_url = "{0}{1}".format(self.base_url, authenticate_uri)
		r = requests.get(
			authenticate_url,
			auth=HTTPBasicAuth(self.app_key, self.app_secret)
		)
		self.authentication_token = r.json()['access_token']
		return r.json()['access_token']

	def get_balance(self, initiator=None, security_credential=None, party_a=None, identifier_type=None,
					remarks=None, queue_timeout_url=None,result_url=None):
		"""
		This method uses Mpesa's Account Balance API to to enquire the balance on a M-Pesa BuyGoods (Till Number).

		Args:
			initiator (str): Username used to authenticate the transaction.
			security_credential (str): Generate from developer portal.
			command_id (str): AccountBalance.
			party_a (int): Till number being queried.
			identifier_type (int): Type of organization receiving the transaction. (MSISDN/Till Number/Organization short code)
			remarks (str): Comments that are sent along with the transaction(maximum 100 characters).
			queue_timeout_url (str): The url that handles information of timed out transactions.
			result_url (str): The url that receives results from M-Pesa api call.

		Returns:
			OriginatorConverstionID (str): The unique request ID for tracking a transaction.
			ConversationID (str): The unique request ID returned by mpesa for each request made
			ResponseDescription (str): Response Description message
		"""

		payload = {
			"Initiator": initiator,
			"SecurityCredential": security_credential,
			"CommandID": "AccountBalance",
			"PartyA": party_a,
			"IdentifierType": identifier_type,
			"Remarks": remarks,
			"QueueTimeOutURL": queue_timeout_url,
			"ResultURL": result_url
		}
		headers = {'Authorization': 'Bearer {0}'.format(self.authentication_token), 'Content-Type': "application/json"}
		saf_url = "{0}{1}".format(self.base_url, "/mpesa/accountbalance/v1/query")
		r = requests.post(saf_url, headers=headers, json=payload)
		return r.json()

	def stk_push(self, business_shortcode=None, passcode=None, amount=None, callback_url=None, reference_code=None,
				 phone_number=None, description=None):
		"""
		This method uses Mpesa's Express API to initiate online payment on behalf of a customer.

		Args:
			business_shortcode (int): The short code of the organization.
			passcode (str): Get from developer portal
			amount (int): The amount being transacted
			callback_url (str): A CallBack URL is a valid secure URL that is used to receive notifications from M-Pesa API.
			reference_code(str): Account Reference: This is an Alpha-Numeric parameter that is defined by your system as an Identifier of the transaction for CustomerPayBillOnline transaction type.
			phone_number(int): The Mobile Number to receive the STK Pin Prompt.
			description(str): This is any additional information/comment that can be sent along with the request from your system. MAX 13 characters

		Success Response:
			CustomerMessage(str): Messages that customers can understand.
			CheckoutRequestID(str): This is a global unique identifier of the processed checkout transaction request.
			ResponseDescription(str): Describes Success or failure
			MerchantRequestID(str): This is a global unique Identifier for any submitted payment request.
			ResponseCode(int): 0 means success all others are error codes. e.g.404.001.03

		Error Reponse:
			requestId(str): This is a unique requestID for the payment request
			errorCode(str): This is a predefined code that indicates the reason for request failure.
			errorMessage(str): This is a predefined code that indicates the reason for request failure.
		"""

		time = str(datetime.datetime.now()).split(".")[0].replace("-", "").replace(" ", "").replace(":", "")
		password = "{0}{1}{2}".format(str(business_shortcode), str(passcode), time)
		encoded = base64.b64encode(bytes(password, encoding='utf8'))
		payload = {
			"BusinessShortCode": business_shortcode,
			"Password": encoded.decode("utf-8"),
			"Timestamp": time,
			"Amount": amount,
			"PartyA": int(phone_number),
			"PartyB": reference_code,
			"PhoneNumber": int(phone_number),
			"CallBackURL": callback_url,
			"AccountReference": reference_code,
			"TransactionDesc": description,
			"TransactionType": "CustomerPayBillOnline" if self.env == "sandbox" else "CustomerBuyGoodsOnline"
		}
		headers = {'Authorization': 'Bearer {0}'.format(self.authentication_token), 'Content-Type': "application/json"}

		saf_url = "{0}{1}".format(self.base_url, "/mpesa/stkpush/v1/processrequest")
		r = requests.post(saf_url, headers=headers, json=payload)
		return r.json()