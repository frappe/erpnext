# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import re
import jwt
import json
import base64
import frappe
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
from frappe.model.document import Document
from frappe import _, get_module_path, scrub
from erpnext.regional.india.utils import get_gst_accounts
from frappe.utils.data import get_datetime, cstr, cint, format_date
from frappe.integrations.utils import make_post_request, make_get_request

class EInvoiceSettings(Document):
	def validate(self):
		mandatory_fields = ['client_id', 'client_secret', 'gstin', 'username', 'password', 'public_key']
		for d in mandatory_fields:
			if not self.get(d):
				frappe.throw(_("{} is required").format(frappe.unscrub(d)), title=_("Missing Values"))
	
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
	
	def aes_encrypt(self, msg, key):
		if not (isinstance(key, bytes) or isinstance(key, bytearray)):
			key = base64.b64decode(key)
		
		cipher = AES.new(key, AES.MODE_ECB)
		bytes_msg = str.encode(msg)
		padded_bytes_msg = pad(bytes_msg, AES.block_size)
		enc_msg = cipher.encrypt(padded_bytes_msg)
		b64_enc_msg = base64.b64encode(enc_msg)
		return b64_enc_msg.decode()
	
	def jwt_decrypt(self, token):
		return jwt.decode(token, verify=False)

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
	
	def get_header(self):
		headers = { 'content-type': 'application/json' }
		headers.update(dict(client_id=self.client_id, client_secret=self.client_secret, user_name=self.username))
		headers.update(dict(Gstin=self.gstin, AuthToken=self.auth_token))

		return headers
	
	def get_gstin_details(self, gstin):
		endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/Master/gstin/{gstin}'.format(gstin=gstin)
		headers = self.get_header()

		res = make_get_request(endpoint, headers=headers)
		self.handle_err_response(res)

		enc_json = res.get('Data')
		json_str = self.aes_decrypt(enc_json, self.sek)
		data = json.loads(json_str)

		return data
	
	def generate_irn(self, invoice):
		endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice'
		headers = self.get_header()

		invoice = frappe.get_doc("Sales Invoice", invoice)
		e_invoice = self.make_e_invoice(invoice)

		enc_e_invoice_json = self.aes_encrypt(e_invoice, self.sek)
		payload = dict(Data=enc_e_invoice_json)

		res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
		self.handle_err_response(res)

		enc_json = res.get('Data')
		json_str = self.aes_decrypt(enc_json, self.sek)

		data = json.loads(json_str)
		self.handle_irn_response(data)

		return data
	
	def get_irn_details(self, irn):
		endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/irn/{irn}'.format(irn=irn)
		headers = self.get_header()

		res = make_get_request(endpoint, headers=headers)
		self.handle_err_response(res)

		enc_json = res.get('Data')
		json_str = self.aes_decrypt(enc_json, self.sek)

		data = json.loads(json_str)
		self.handle_irn_response(data)

		return data

	def cancel_irn(self, irn, reason, remark=''):
		endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/Cancel'
		headers = self.get_header()

		cancel_e_inv = json.dumps(dict(Irn=irn, CnlRsn=reason, CnlRem=remark))
		enc_json = self.aes_encrypt(cancel_e_inv, self.sek)
		payload = dict(Data=enc_json)

		res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
		self.handle_err_response(res)

		return res
	
	def handle_irn_response(self, data):
		enc_signed_invoice = data['SignedInvoice']
		enc_signed_qr_code = data['SignedQRCode']
		signed_invoice = self.jwt_decrypt(enc_signed_invoice)['data']
		signed_qr_code = self.jwt_decrypt(enc_signed_qr_code)['data']
		data['DecryptedSignedInvoice'] = json.loads(signed_invoice)
		data['DecryptedSignedQRCode'] = json.loads(signed_qr_code)

	def handle_err_response(self, response):
		if response.get('Status') == 0:
			err_details = response.get('ErrorDetails')
			print(response)
			err_msg = ""
			for d in err_details:
				err_msg += d.get('ErrorMessage')
				err_msg += "<br>"
			frappe.throw(_(err_msg), title=_('API Request Failed'))

	def read_json(self, name):
		file_path = os.path.join(os.path.dirname(__file__), "{name}.json".format(name=name))
		with open(file_path, 'r') as f:
			return cstr(f.read())

	def get_trans_details(self, invoice):
		supply_type = ''
		if invoice.gst_category == 'Registered Regular': supply_type = 'B2B'
		elif invoice.gst_category == 'SEZ': supply_type = 'SEZWOP'
		elif invoice.gst_category == 'Overseas': supply_type = 'EXPWOP'
		elif invoice.gst_category == 'Deemed Export': supply_type = 'DEXP'

		if not supply_type: 
			return _('Invalid invoice transaction category.')

		return frappe._dict(dict(
			tax_scheme='GST', supply_type=supply_type, reverse_charge=invoice.reverse_charge
		))

	def get_doc_details(self, invoice):
		invoice_type = 'CRN' if invoice.is_return else 'INV'
		invoice_name = invoice.name
		invoice_date = format_date(invoice.posting_date, 'dd/mm/yyyy')

		return frappe._dict(dict(
			invoice_type=invoice_type, invoice_name=invoice_name, invoice_date=invoice_date
		))

	def get_party_gstin_details(self, party_address):
		gstin, address_line1, address_line2, phone, email_id = frappe.db.get_value(
			"Address", party_address, ["gstin", "address_line1", "address_line2", "phone", "email_id"]
		)
		gstin_details = self.get_gstin_details(gstin)
		legal_name = gstin_details.get('LegalName')
		trade_name = gstin_details.get('TradeName')
		location = gstin_details.get('AddrLoc')
		state_code = gstin_details.get('StateCode')
		pincode = cint(gstin_details.get('AddrPncd'))
		if state_code == 97:
			pincode = 999999

		return frappe._dict(dict(
			gstin=gstin, legal_name=legal_name, trade_name=trade_name, location=location,
			pincode=pincode, state_code=state_code, address_line1=address_line1,
			address_line2=address_line2, email=email_id, phone=phone
		))
	
	def get_overseas_address_details(self, party_address):
		address_title, address_line1, address_line2, city, phone, email_id = frappe.db.get_value(
			"Address", party_address, ["address_title", "address_line1", "address_line2", "city", "phone", "email_id"]
		)

		return frappe._dict(dict(
			gstin='URP', legal_name=address_title, address_line1=address_line1,
			address_line2=address_line2, email=email_id, phone=phone,
			pincode=999999, state_code=96, place_of_supply=96, location=city
		))
	
	def get_item_list(self, invoice):
		item_list = []
		gst_accounts = get_gst_accounts(invoice.company)
		gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

		for d in invoice.items:
			item_schema = self.read_json("e_inv_item_schema")
			item = frappe._dict(dict())
			item.update(d.as_dict())
			item.sr_no = d.idx
			item.description = d.item_name
			item.is_service_item = "N" if frappe.db.get_value("Item", d.item_code, "is_stock_item") else "Y"
			item.batch_expiry_date = frappe.db.get_value("Batch", d.batch_no, "expiry_date") if d.batch_no else None
			item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
			item.tax_rate = 0
			item.igst_amount = 0
			item.cgst_amount = 0
			item.sgst_amount = 0
			item.cess_rate = 0
			item.cess_amount = 0
			for t in invoice.taxes:
				if t.account_head in gst_accounts_list:
					item_tax_detail = json.loads(t.item_wise_tax_detail).get(item.item_code)
					if t.account_head in gst_accounts.cess_account:
						item.cess_rate += item_tax_detail[0]
						item.cess_amount += item_tax_detail[1]
					elif t.account_head in gst_accounts.igst_account:
						item.tax_rate += item_tax_detail[0]
						item.igst_amount += item_tax_detail[1]
					elif t.account_head in gst_accounts.sgst_account:
						item.tax_rate += item_tax_detail[0]
						item.sgst_amount += item_tax_detail[1]
					elif t.account_head in gst_accounts.cgst_account:
						item.tax_rate += item_tax_detail[0]
						item.cgst_amount += item_tax_detail[1]
			
			item.total_value = item.base_amount + item.igst_amount + item.sgst_amount + item.cgst_amount + item.cess_amount
			e_inv_item = item_schema.format(item=item)
			item_list.append(e_inv_item)

		return ", ".join(item_list)

	def get_value_details(self, invoice):
		gst_accounts = get_gst_accounts(invoice.company)
		gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

		value_details = frappe._dict(dict())
		value_details.base_net_total = invoice.base_net_total
		value_details.invoice_discount_amt = invoice.discount_amount
		value_details.round_off = invoice.base_rounding_adjustment
		value_details.base_grand_total = invoice.base_rounded_total
		value_details.grand_total = invoice.rounded_total
		value_details.total_cgst_amt = 0
		value_details.total_sgst_amt = 0
		value_details.total_igst_amt = 0
		value_details.total_cess_amt = 0
		for t in invoice.taxes:
			if t.account_head in gst_accounts_list:
				if t.account_head in gst_accounts.cess_account:
					value_details.total_cess_amt += t.base_tax_amount
				elif t.account_head in gst_accounts.igst_account:
					value_details.total_igst_amt += t.base_tax_amount
				elif t.account_head in gst_accounts.sgst_account:
					value_details.total_sgst_amt += t.base_tax_amount
				elif t.account_head in gst_accounts.cgst_account:
					value_details.total_cgst_amt += t.base_tax_amount
		
		return value_details
	
	def get_payment_details(self, invoice):
		payee_name = invoice.company
		mode_of_payment = ", ".join([d.mode_of_payment for d in invoice.payments])
		paid_amount = invoice.base_paid_amount
		outstanding_amount = invoice.outstanding_amount

		return frappe._dict(dict(
			payee_name=payee_name, mode_of_payment=mode_of_payment,
			paid_amount=paid_amount, outstanding_amount=outstanding_amount
		))
	
	def get_return_doc_reference(self, invoice):
		invoice_date = frappe.db.get_value("Sales Invoice", invoice.return_against, "posting_date")
		return frappe._dict(dict(
			invoice_name=invoice.return_against, invoice_date=invoice_date
		))

	def make_e_invoice(self, invoice):
		schema = self.read_json("e_inv_schema")
		validations = self.read_json("e_inv_validation")
		validations = json.loads(validations)

		trans_details = self.get_trans_details(invoice)
		doc_details = self.get_doc_details(invoice)
		seller_details = self.get_party_gstin_details(invoice.company_address)

		if invoice.gst_category == 'Overseas':
			buyer_details = self.get_overseas_address_details(invoice.customer_address)
		else:
			buyer_details = self.get_party_gstin_details(invoice.customer_address)
			place_of_supply = invoice.place_of_supply.split('-')[0]
			buyer_details.update(dict(place_of_supply=place_of_supply))

		item_list = self.get_item_list(invoice)
		value_details = self.get_value_details(invoice)

		dispatch_details = frappe._dict({})
		period_details = frappe._dict({})
		shipping_details = frappe._dict({})
		export_details = frappe._dict({})
		eway_bill_details = frappe._dict({})
		if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
			shipping_details = self.get_party_gstin_details(invoice.shipping_address_name)
		
		payment_details = frappe._dict({})
		if invoice.is_pos and invoice.base_paid_amount:
			payment_details = self.get_payment_details(invoice)
		
		prev_doc_details = frappe._dict({})
		if invoice.is_return and invoice.return_against:
			prev_doc_details = self.get_return_doc_reference(invoice)

		e_invoice = schema.format(
			trans_details=trans_details, doc_details=doc_details, dispatch_details=dispatch_details,
			seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
			item_list=item_list, value_details=value_details, payment_details=payment_details,
			period_details=period_details, prev_doc_details=prev_doc_details,
			export_details=export_details, eway_bill_details=eway_bill_details
		)
		e_invoice = json.loads(e_invoice)

		self.run_e_invoice_validations(validations, e_invoice)

		return json.dumps(e_invoice)
	
	def run_e_invoice_validations(self, validations, e_invoice):
		type_map = {
			"string": cstr,
			"number": cint,
			"object": dict,
			"array": list
		}
		# validate root mandatory keys
		mandatory_fields = validations.get('required')
		if mandatory_fields and not set(mandatory_fields).issubset(set(e_invoice.keys())):
			print("Mandatory condition failed")
		
		for field, value in validations.items():
			if isinstance(value, list): value = value[0]

			invoice_value = e_invoice.get(field)
			if not invoice_value:
				print(field, "value undefined")
				continue

			should_be_of_type = type_map[value.get('type').lower()]
			if should_be_of_type == dict:
				properties = value.get('properties')

				if isinstance(invoice_value, list):
					for d in invoice_value:
						self.run_e_invoice_validations(properties, d)
				else:
					self.run_e_invoice_validations(properties, invoice_value)
					if not invoice_value:
						e_invoice.pop(field, None)
				continue
			
			if invoice_value == "None":
				e_invoice.pop(field, None)
				continue

			e_invoice[field] = should_be_of_type(invoice_value) if e_invoice[field] else e_invoice[field]
			
			should_be_of_len = value.get('maxLength')
			should_be_greater_than = value.get('minimum')
			should_be_less_than = value.get('maximum')
			pattern_str = value.get('pattern')
			pattern = re.compile(pattern_str or "")

			if should_be_of_type == 'string' and not len(invoice_value) <= should_be_of_len:
				print("Max Length Exceeded", field, invoice_value)
			if should_be_of_type == 'number' and not (should_be_greater_than <= invoice_value <= should_be_of_len):
				print("Value too large", field, invoice_value)
			if pattern_str and not pattern.match(invoice_value):
				print("Pattern Mismatch", field, invoice_value)
