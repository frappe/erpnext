# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import json
import base64
import frappe
from frappe import _
from frappe.utils import cstr
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
from frappe.utils.data import get_datetime
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request, make_get_request

class EInvoiceSettings(Document):
	def validate(self):
		pass
	
	def before_save(self):
		if not self.public_key or self.has_value_changed('public_key_file'):
			self.public_key = self.read_key_file()

	def read_key_file(self):
		key_file = frappe.get_doc('File', dict(attached_to_name=self.doctype, attached_to_field='public_key_file'))
		with open(key_file.get_full_path(), 'rb') as f:
			return cstr(f.read())
	
	def rsa_encrypt(self, msg, key):
		if not (isinstance(msg, bytes) or isinstance(msg, bytearray)):
			msg = str.encode(msg)

		rsa_pub_key = RSA.import_key(key)
		cipher = PKCS1_v1_5.new(rsa_pub_key)
		enc_msg = cipher.encrypt(msg)
		b64_enc_msg = base64.b64encode(enc_msg)
		return b64_enc_msg.decode()
	
	def aes_decrypt(self, enc_msg, key):
		encode_as_b64 = True
		if not (isinstance(key, bytes) or isinstance(key, bytearray)):
			key = base64.b64decode(key)
			encode_as_b64 = False

		cipher = AES.new(key, AES.MODE_ECB)
		b64_enc_msg = base64.b64decode(enc_msg)
		msg_bytes = cipher.decrypt(b64_enc_msg)
		msg_bytes = unpad(msg_bytes, AES.block_size) # due to ECB/PKCS5Padding
		if encode_as_b64:
			msg_bytes = base64.b64encode(msg_bytes)
		return msg_bytes.decode()

	def make_authentication_request(self):
		endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/auth'
		headers = { 'content-type': 'application/json' }
		headers.update(dict(client_id=self.client_id, client_secret=self.client_secret))
		payload = dict(UserName=self.username, ForceRefreshAccessToken=bool(self.auto_refresh_token))

		appkey = bytearray(os.urandom(32))
		enc_appkey = self.rsa_encrypt(appkey, self.public_key)

		password = self.get_password(fieldname='password')
		enc_password = self.rsa_encrypt(password, self.public_key)

		payload.update(dict(Password=enc_password, AppKey=enc_appkey))

		res = make_post_request(endpoint, headers=headers, data=json.dumps({ 'data': payload }))
		self.handle_err_response(res)

		self.extract_token_and_sek(res, appkey)

	def extract_token_and_sek(self, response, appkey):
		data = response.get('Data')
		auth_token = data.get('AuthToken')
		token_expiry = data.get('TokenExpiry')
		enc_sek = data.get('Sek')
		sek = self.aes_decrypt(enc_sek, appkey)

		self.auth_token = auth_token
		self.token_expiry = get_datetime(token_expiry)
		self.sek = sek
		self.save()
	
	def get_gstin_details(self, gstin):
		endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/Master/gstin/{gstin}'.format(gstin=gstin)
		headers = { 'content-type': 'application/json' }
		headers.update(dict(client_id=self.client_id, client_secret=self.client_secret, user_name=self.username))
		headers.update(dict(Gstin=self.gstin, AuthToken=self.auth_token))

		res = make_get_request(endpoint, headers=headers)
		self.handle_err_response(res)

		enc_json = res.get('Data')
		json_str = self.aes_decrypt(enc_json, self.sek)
		data = json.loads(json_str)

		return data

	def handle_err_response(self, response):
		if response.get('Status') == 0:
			err_msg = response.get('ErrorDetails')[0].get('ErrorMessage')
			frappe.throw(_(err_msg), title=_("API Request Failed"))