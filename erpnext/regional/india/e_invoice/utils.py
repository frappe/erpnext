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
from six import string_types
from Crypto.PublicKey import RSA
from pyqrcode import create as qrcreate
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
from frappe.model.document import Document
from frappe import _, get_module_path, scrub, bold
from frappe.integrations.utils import make_post_request, make_get_request
from erpnext.regional.india.utils import get_gst_accounts, get_place_of_supply
from frappe.utils.data import get_datetime, cstr, cint, format_date, flt, time_diff_in_seconds, now_datetime

def validate_einvoice_fields(doc):
	einvoicing_enabled = frappe.db.get_value('E Invoice Settings', 'E Invoice Settings', 'enable')
	invalid_doctype = doc.doctype not in ['Sales Invoice']
	invalid_supply_type = doc.get('gst_category') not in ['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export']

	if invalid_doctype or invalid_supply_type or not einvoicing_enabled: return

	if doc.docstatus == 0 and doc._action == 'save':
		if doc.irn:
			frappe.throw(_('You cannot edit the invoice after generating IRN'), title=_('Edit Not Allowed'))
		if len(doc.name) > 16:
			title = _('Document Name Too Long')
			msg = (_('As you have E-Invoicing enabled, To be able to generate IRN for this invoice, document name {} exceed 16 letters. ')
						.format(bold(_('should not'))))
			msg += '<br><br>'
			msg += (_('You {} modify your {} in order to have document name of {} length of 16. ')
						.format(bold(_('must')), bold(_('naming series')), bold(_('maximum'))))
			frappe.throw(msg, title=title)

	elif doc.docstatus == 1 and doc._action == 'submit' and not doc.irn:
		frappe.throw(_('You must generate IRN before submitting the document.'), title=_('Missing IRN'))

	elif doc.docstatus == 2 and doc._action == 'cancel' and not doc.irn_cancelled:
		frappe.throw(_('You must cancel IRN before cancelling the document.'), title=_('Cancel Not Allowed'))

def get_credentials():
	doc = frappe.get_doc('E Invoice Settings')
	if not doc.enable:
		frappe.throw(_("To setup E Invoicing you need to enable E Invoice Settings first."), title=_("E Invoicing Disabled"))

	if not doc.token_expiry or time_diff_in_seconds(now_datetime(), doc.token_expiry) > 5.0:
		fetch_token(doc)
		doc.load_from_db()

	return doc

def rsa_encrypt(msg, key):
	if not (isinstance(msg, bytes) or isinstance(msg, bytearray)):
		msg = str.encode(msg)

	rsa_pub_key = RSA.import_key(key)
	cipher = PKCS1_v1_5.new(rsa_pub_key)
	enc_msg = cipher.encrypt(msg)
	b64_enc_msg = base64.b64encode(enc_msg)
	return b64_enc_msg.decode()

def aes_decrypt(enc_msg, key):
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

def aes_encrypt(msg, key):
	if not (isinstance(key, bytes) or isinstance(key, bytearray)):
		key = base64.b64decode(key)
	
	cipher = AES.new(key, AES.MODE_ECB)
	bytes_msg = str.encode(msg)
	padded_bytes_msg = pad(bytes_msg, AES.block_size)
	enc_msg = cipher.encrypt(padded_bytes_msg)
	b64_enc_msg = base64.b64encode(enc_msg)
	return b64_enc_msg.decode()

def jwt_decrypt(token):
	return jwt.decode(token, verify=False)

def get_header(creds):
	headers = { 'content-type': 'application/json' }
	headers.update(dict(client_id=creds.client_id, client_secret=creds.client_secret, user_name=creds.username))
	headers.update(dict(Gstin=creds.gstin, AuthToken=creds.auth_token))
	return headers

@frappe.whitelist()
def fetch_token(credentials=None):
	if not credentials:
		credentials = frappe.get_doc('E Invoice Settings')

	endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/auth'
	headers = { 'content-type': 'application/json' }
	headers.update(dict(client_id=credentials.client_id, client_secret=credentials.client_secret))
	payload = dict(UserName=credentials.username, ForceRefreshAccessToken=bool(credentials.auto_refresh_token))

	appkey = bytearray(os.urandom(32))
	enc_appkey = rsa_encrypt(appkey, credentials.public_key)

	password = credentials.get_password(fieldname='password')
	enc_password = rsa_encrypt(password, credentials.public_key)

	payload.update(dict(Password=enc_password, AppKey=enc_appkey))

	res = make_post_request(endpoint, headers=headers, data=json.dumps({ 'data': payload }))
	handle_err_response(res)

	auth_token, token_expiry, sek = extract_token_and_sek(res, appkey)

	credentials.auth_token = auth_token
	credentials.token_expiry = get_datetime(token_expiry)
	credentials.sek = sek
	credentials.save()

def extract_token_and_sek(response, appkey):
	data = response.get('Data')
	auth_token = data.get('AuthToken')
	token_expiry = data.get('TokenExpiry')
	enc_sek = data.get('Sek')
	sek = aes_decrypt(enc_sek, appkey)
	return auth_token, token_expiry, sek

def attach_signed_invoice(doctype, name, data):
	f = frappe.get_doc({
		'doctype': 'File',
		'file_name': 'E-INV--{}.json'.format(name),
		'attached_to_doctype': doctype,
		'attached_to_name': name,
		'content': json.dumps(data),
		'is_private': True
	}).insert()

def get_gstin_details(gstin):
	credentials = get_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/Master/gstin/{gstin}'.format(gstin=gstin)
	headers = get_header(credentials)

	res = make_get_request(endpoint, headers=headers)
	handle_err_response(res)

	enc_details = res.get('Data')
	json_str = aes_decrypt(enc_details, credentials.sek)
	details = json.loads(json_str)

	return details

@frappe.whitelist()
def generate_irn(doctype, name):
	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice'
	credentials = get_credentials()
	headers = get_header(credentials)

	einvoice = make_einvoice(doctype, name)
	einvoice = json.dumps(einvoice)

	enc_einvoice_json = aes_encrypt(einvoice, credentials.sek)
	payload = dict(Data=enc_einvoice_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	res = handle_err_response(res)

	enc_json = res.get('Data')
	json_str = aes_decrypt(enc_json, credentials.sek)

	signed_einvoice = json.loads(json_str)
	decrypt_irn_response(signed_einvoice)

	update_einvoice_fields(doctype, name, signed_einvoice)

	attach_qrcode_image(doctype, name)
	attach_signed_invoice(doctype, name, signed_einvoice['DecryptedSignedInvoice'])

	return signed_einvoice

def get_irn_details(irn):
	credentials = get_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/irn/{irn}'.format(irn=irn)
	headers = get_header(credentials)

	res = make_get_request(endpoint, headers=headers)
	handle_err_response(res)

	return res

@frappe.whitelist()
def cancel_irn(doctype, name, irn, reason, remark=''):
	credentials = get_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/Cancel'
	headers = get_header(credentials)

	cancel_einv = json.dumps(dict(Irn=irn, CnlRsn=reason, CnlRem=remark))
	enc_json = aes_encrypt(cancel_einv, credentials.sek)
	payload = dict(Data=enc_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	handle_err_response(res)

	frappe.db.set_value(doctype, name, 'irn_cancelled', 1)

	return res

@frappe.whitelist()
def cancel_eway_bill(doctype, name, eway_bill, reason, remark=''):
	credentials = get_credentials()
	endpoint = 'https://einv-apisandbox.nic.in/ewaybillapi/v1.03/ewayapi'
	headers = get_header(credentials)

	cancel_eway_bill_json = json.dumps(dict(ewbNo=eway_bill, cancelRsnCode=reason, cancelRmrk=remark))
	enc_json = aes_encrypt(cancel_eway_bill_json, credentials.sek)
	payload = dict(action='CANEWB', Data=enc_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	handle_err_response(res)

	frappe.db.set_value(doctype, name, 'ewaybill', '')
	frappe.db.set_value(doctype, name, 'eway_bill_cancelled', 1)

	return res

def decrypt_irn_response(data):
	enc_signed_invoice = data['SignedInvoice']
	enc_signed_qr_code = data['SignedQRCode']
	signed_invoice = jwt_decrypt(enc_signed_invoice)['data']
	signed_qr_code = jwt_decrypt(enc_signed_qr_code)['data']
	data['DecryptedSignedInvoice'] = json.loads(signed_invoice)
	data['DecryptedSignedQRCode'] = json.loads(signed_qr_code)

def handle_err_response(response):
	if response.get('Status') == 0:
		err_details = response.get('ErrorDetails')
		errors = []
		for d in err_details:
			err_code = d.get('ErrorCode')

			if err_code == '2150':
				irn = [d['Desc']['Irn'] for d in response.get('InfoDtls') if d['InfCd'] == 'DUPIRN']
				response = get_irn_details(irn[0])
				return response

			errors.append(d.get('ErrorMessage'))

		if errors:
			frappe.log_error(title="E Invoice API Request Failed", message=json.dumps(errors, default=str, indent=4))
			if len(errors) > 1:
				li = ['<li>'+ d +'</li>' for d in errors]
				frappe.throw(_("""<ul style='padding-left: 20px'>{}</ul>""").format(''.join(li)), title=_('API Request Failed'))
			else:
				frappe.throw(errors[0], title=_('API Request Failed'))

	return response

def read_json(name):
	file_path = os.path.join(os.path.dirname(__file__), '{name}.json'.format(name=name))
	with open(file_path, 'r') as f:
		return cstr(f.read())

def get_trans_details(invoice):
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

def get_doc_details(invoice):
	if invoice.doctype == 'Purchase Invoice' and invoice.is_return:
		invoice_type = 'DBN'
	else:
		invoice_type = 'CRN' if invoice.is_return else 'INV'

	invoice_name = invoice.name
	invoice_date = format_date(invoice.posting_date, 'dd/mm/yyyy')

	return frappe._dict(dict(invoice_type=invoice_type, invoice_name=invoice_name, invoice_date=invoice_date))

def get_party_gstin_details(address_name):
	address = frappe.get_all('Address', filters={'name': address_name}, fields=['*'])[0]

	gstin = address.get('gstin')
	gstin_details = get_gstin_details(gstin)
	legal_name = gstin_details.get('LegalName')
	trade_name = gstin_details.get('TradeName')
	location = gstin_details.get('AddrLoc')
	state_code = gstin_details.get('StateCode')
	pincode = cint(gstin_details.get('AddrPncd'))
	address_line1 = '{} {}'.format(gstin_details.get('AddrBno'), gstin_details.get('AddrFlno'))
	address_line2 = '{} {}'.format(gstin_details.get('AddrBnm'), gstin_details.get('AddrSt'))
	email_id = address.get('email_id')
	phone = address.get('phone')
	if state_code == 97:
		pincode = 999999

	return frappe._dict(dict(
		gstin=gstin, legal_name=legal_name, location=location,
		pincode=pincode, state_code=state_code, address_line1=address_line1,
		address_line2=address_line2, email=email_id, phone=phone
	))

def get_overseas_address_details(address_name):
	address_title, address_line1, address_line2, city, phone, email_id = frappe.db.get_value(
		'Address', address_name, ['address_title', 'address_line1', 'address_line2', 'city', 'phone', 'email_id']
	)

	return frappe._dict(dict(
		gstin='URP', legal_name=address_title, address_line1=address_line1,
		address_line2=address_line2, email=email_id, phone=phone,
		pincode=999999, state_code=96, place_of_supply=96, location=city
	))

def get_item_list(invoice):
	item_list = []
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	for d in invoice.items:
		item_schema = read_json('einv_item_template')
		item = frappe._dict({})
		item.update(d.as_dict())
		item.sr_no = d.idx
		item.description = d.item_name
		item.is_service_item = 'N' if frappe.db.get_value('Item', d.item_code, 'is_stock_item') else 'Y'
		item.batch_expiry_date = frappe.db.get_value('Batch', d.batch_no, 'expiry_date') if d.batch_no else None
		item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
		item.qty = abs(item.qty)
		item.unit_rate = abs(item.base_price_list_rate) if item.discount_amount else abs(item.base_rate)
		item.total_amount = abs(item.unit_rate * item.qty)
		item.discount_amount = abs(item.discount_amount * item.qty)
		item.base_amount = abs(item.base_amount)
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
					item.cess_amount += abs(item_tax_detail[1])
				elif t.account_head in gst_accounts.igst_account:
					item.tax_rate += item_tax_detail[0]
					item.igst_amount += abs(item_tax_detail[1])
				elif t.account_head in gst_accounts.sgst_account:
					item.tax_rate += item_tax_detail[0]
					item.sgst_amount += abs(item_tax_detail[1])
				elif t.account_head in gst_accounts.cgst_account:
					item.tax_rate += item_tax_detail[0]
					item.cgst_amount += abs(item_tax_detail[1])
		
		item.total_value = abs(item.base_amount + item.igst_amount + item.sgst_amount + item.cgst_amount + item.cess_amount)
		einv_item = item_schema.format(item=item)
		item_list.append(einv_item)

	return ', '.join(item_list)

def get_value_details(invoice):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	value_details = frappe._dict(dict())
	value_details.base_net_total = abs(invoice.base_net_total)
	value_details.invoice_discount_amt = abs(invoice.discount_amount)
	value_details.round_off = abs(invoice.base_rounding_adjustment)
	value_details.base_grand_total = abs(invoice.base_rounded_total)
	value_details.grand_total = abs(invoice.rounded_total)
	value_details.total_cgst_amt = 0
	value_details.total_sgst_amt = 0
	value_details.total_igst_amt = 0
	value_details.total_cess_amt = 0
	for t in invoice.taxes:
		if t.account_head in gst_accounts_list:
			if t.account_head in gst_accounts.cess_account:
				value_details.total_cess_amt += abs(t.base_tax_amount_after_discount_amount)
			elif t.account_head in gst_accounts.igst_account:
				value_details.total_igst_amt += abs(t.base_tax_amount_after_discount_amount)
			elif t.account_head in gst_accounts.sgst_account:
				value_details.total_sgst_amt += abs(t.base_tax_amount_after_discount_amount)
			elif t.account_head in gst_accounts.cgst_account:
				value_details.total_cgst_amt += abs(t.base_tax_amount_after_discount_amount)
	
	return value_details

def get_payment_details(invoice):
	payee_name = invoice.company
	mode_of_payment = ', '.join([d.mode_of_payment for d in invoice.payments])
	paid_amount = invoice.base_paid_amount
	outstanding_amount = invoice.outstanding_amount

	return frappe._dict(dict(
		payee_name=payee_name, mode_of_payment=mode_of_payment,
		paid_amount=paid_amount, outstanding_amount=outstanding_amount
	))

def get_return_doc_reference(invoice):
	invoice_date = frappe.db.get_value('Sales Invoice', invoice.return_against, 'posting_date')
	return frappe._dict(dict(
		invoice_name=invoice.return_against, invoice_date=format_date(invoice_date, 'dd/mm/yyyy')
	))

def get_eway_bill_details(invoice):
	if not invoice.distance:
		frappe.throw(_('Distance is mandatory for E-Way Bill generation'), title=_('E Invoice Validation Failed'))

	mode_of_transport = { 'Road': '1', 'Air': '2', 'Rail': '3', 'Ship': '4' }
	vehicle_type = { 'Regular': 'R', 'Over Dimensional Cargo (ODC)': 'O' }

	return frappe._dict(dict(
		gstin=invoice.gst_transporter_id,
		name=invoice.transporter_name,
		mode_of_transport=mode_of_transport[invoice.mode_of_transport],
		distance=invoice.distance,
		document_name=invoice.lr_no,
		document_date=format_date(invoice.lr_date, 'dd/mm/yyyy'),
		vehicle_no=invoice.vehicle_no,
		vehicle_type=vehicle_type[invoice.gst_vehicle_type]
	))

@frappe.whitelist()
def make_einvoice(doctype, name):
	invoice = frappe.get_doc(doctype, name)
	schema = read_json('einv_template')

	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	value_details = get_value_details(invoice)
	trans_details = get_trans_details(invoice)
	seller_details = get_party_gstin_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_gstin_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, doctype) or invoice.billing_address_gstin
		place_of_supply = place_of_supply[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))
	
	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		shipping_details = get_party_gstin_details(invoice.shipping_address_name)
	
	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)
	
	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)
	
	if invoice.transporter:
		eway_bill_details = get_eway_bill_details(invoice)
	
	# not yet implemented
	dispatch_details = period_details = export_details = frappe._dict({})

	einvoice = schema.format(
		trans_details=trans_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, value_details=value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)
	einvoice = json.loads(einvoice)
	
	validations = json.loads(read_json('einv_validation'))
	errors = validate_einvoice(validations, einvoice, [])
	if errors:
		frappe.log_error(title="E Invoice Validation Failed", message=json.dumps(errors, default=str, indent=4))
		if len(errors) > 1:
			li = ['<li>'+ d +'</li>' for d in errors]
			frappe.throw("<ul style='padding-left: 20px'>{}</ul>".format(''.join(li)), title=_('E Invoice Validation Failed'))
		else:
			frappe.throw(errors[0], title=_('E Invoice Validation Failed'))

	return einvoice

def validate_einvoice(validations, einvoice, errors=[]):
	for fieldname, field_validation in validations.items():
		value = einvoice.get(fieldname, None)
		if not value or value == "None":
			# remove keys with empty values
			einvoice.pop(fieldname, None)
			continue

		value_type = field_validation.get("type").lower()
		if value_type in ['object', 'array']:
			child_validations = field_validation.get('properties')

			if isinstance(value, list):
				for d in value:
					validate_einvoice(child_validations, d, errors)
					if not d:
						# remove empty dicts
						einvoice.pop(fieldname, None)
			else:
				validate_einvoice(child_validations, value, errors)
				if not value:
					# remove empty dicts
					einvoice.pop(fieldname, None)
			continue
		
		# convert to int or str
		if value_type == 'string':
			einvoice[fieldname] = str(value)
		elif value_type == 'number':
			einvoice[fieldname] = flt(value, 2) if fieldname != 'Pin' or fieldname != 'Distance' else int(value)

		max_length = field_validation.get('maxLength')
		minimum = flt(field_validation.get('minimum'))
		maximum = flt(field_validation.get('maximum'))
		pattern_str = field_validation.get('pattern')
		pattern = re.compile(pattern_str or '')

		label = field_validation.get('label') or fieldname

		if value_type == 'string' and len(value) > max_length:
			errors.append(_('{} should not exceed {} characters').format(label, max_length))
		if value_type == 'number' and not (flt(value) <= maximum):
			errors.append(_('{} should be less than {}').format(label, maximum))
		if pattern_str and not pattern.match(value):
			errors.append(field_validation.get('validationMsg'))
	
	return errors

def update_einvoice_fields(doctype, name, signed_einvoice):
	enc_signed_invoice = signed_einvoice.get('SignedInvoice')
	decrypted_signed_invoice = jwt_decrypt(enc_signed_invoice)['data']

	if json.loads(decrypted_signed_invoice)['DocDtls']['No'] != name:
		frappe.throw(
			_("Document number of uploaded Signed E-Invoice doesn't matches with Sales Invoice"),
			title=_("Inappropriate E-Invoice")
		)

	frappe.db.set_value(doctype, name, 'irn', signed_einvoice.get('Irn'))
	frappe.db.set_value(doctype, name, 'ewaybill', signed_einvoice.get('EwbNo'))
	frappe.db.set_value(doctype, name, 'signed_qr_code', signed_einvoice.get('SignedQRCode').split('.')[1])
	frappe.db.set_value(doctype, name, 'signed_einvoice', decrypted_signed_invoice)

@frappe.whitelist()
def download_einvoice():
	data = frappe._dict(frappe.local.form_dict)
	einvoice = data['einvoice']
	name = data['name']

	frappe.response['filename'] = 'E-Invoice-' + name + '.json'
	frappe.response['filecontent'] = einvoice
	frappe.response['content_type'] = 'application/json'
	frappe.response['type'] = 'download'

@frappe.whitelist()
def upload_einvoice():
	signed_einvoice = json.loads(frappe.local.uploaded_file)
	data = frappe._dict(frappe.local.form_dict)
	doctype = data['doctype']
	name = data['docname']

	update_einvoice_fields(doctype, name, signed_einvoice)
	attach_qrcode_image(doctype, name)

@frappe.whitelist()
def download_cancel_einvoice():
	data = frappe._dict(frappe.local.form_dict)
	name = data['name']
	irn = data['irn']
	reason = data['reason']
	remark = data['remark']

	cancel_einvoice = json.dumps([dict(Irn=irn, CnlRsn=reason, CnlRem=remark)])

	frappe.response['filename'] = 'Cancel E-Invoice ' + name + '.json'
	frappe.response['filecontent'] = cancel_einvoice
	frappe.response['content_type'] = 'application/json'
	frappe.response['type'] = 'download'

@frappe.whitelist()
def upload_cancel_ack():
	cancel_ack = json.loads(frappe.local.uploaded_file)
	data = frappe._dict(frappe.local.form_dict)
	doctype = data['doctype']
	name = data['docname']

	frappe.db.set_value(doctype, name, 'irn_cancelled', 1)

def attach_qrcode_image(doctype, name):
	qrcode = frappe.db.get_value(doctype, name, 'signed_qr_code')

	if not qrcode: return

	_file = frappe.get_doc({
		'doctype': 'File',
		'file_name': 'Signed_QR_{name}.png'.format(name=name),
		'attached_to_doctype': doctype,
		'attached_to_name': name,
		'content': 'qrcode'
	})
	_file.save()
	frappe.db.commit()
	url = qrcreate(qrcode)
	abs_file_path = os.path.abspath(_file.get_full_path())
	url.png(abs_file_path, scale=2)

	frappe.db.set_value(doctype, name, 'qrcode_image', _file.file_url)