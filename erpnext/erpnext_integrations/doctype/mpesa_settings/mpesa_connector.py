import requests
import datetime

class MpesaConnector():
	def __init__(self, env="sandbox", app_key=None, app_secret=None, sandbox_url="https://sandbox.safaricom.co.ke",
		live_url="https://safaricom.co.ke"):
		self.env = env
		self.app_key = app_key
		self.app_secret = app_secret
		self.sandbox_url = sandbox_url
		self.live_url = live_url
		self.authenticate()