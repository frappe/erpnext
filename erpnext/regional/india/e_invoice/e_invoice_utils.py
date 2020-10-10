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
from pyqrcode import create as qrcreate
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
from frappe.model.document import Document
from frappe import _, get_module_path, scrub
from erpnext.regional.india.utils import get_gst_accounts
from frappe.integrations.utils import make_post_request, make_get_request
from frappe.utils.data import get_datetime, cstr, cint, format_date, flt, time_diff_in_seconds, now_datetime

def validate_einvoice_fields(doc):
	e_invoice_enabled = frappe.db.get_value("E Invoice Settings", "E Invoice Settings", "enable")
	if not doc.doctype in ['Sales Invoice', 'Purchase Invoice'] or not e_invoice_enabled: return

	if doc.docstatus == 0 and doc._action == 'save' and doc.irn:
		frappe.throw(_("You cannot edit the invoice after generating IRN"), title=_("Edit Not Allowed"))
	elif doc.docstatus == 1 and doc._action == 'submit' and not doc.irn:
		frappe.throw(_("You must generate IRN before submitting the document."), title=_("Missing IRN"))
	elif doc.docstatus == 2 and doc._action == 'cancel' and not doc.irn_cancelled:
		frappe.throw(_("You must cancel IRN before cancelling the document."), title=_("Cancel Not Allowed"))

def get_einv_credentials(for_token=False):
	creds = frappe.get_doc("E Invoice Settings")
	if not for_token and (not creds.token_expiry or time_diff_in_seconds(now_datetime(), creds.token_expiry) > 5.0):
		fetch_token()
		creds.load_from_db()
	
	return creds

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
def fetch_token():
	einv_creds = get_einv_credentials(for_token=True)

	endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/auth'
	headers = { 'content-type': 'application/json' }
	headers.update(dict(client_id=einv_creds.client_id, client_secret=einv_creds.client_secret))
	payload = dict(UserName=einv_creds.username, ForceRefreshAccessToken=bool(einv_creds.auto_refresh_token))

	appkey = bytearray(os.urandom(32))
	enc_appkey = rsa_encrypt(appkey, einv_creds.public_key)

	password = einv_creds.get_password(fieldname='password')
	enc_password = rsa_encrypt(password, einv_creds.public_key)

	payload.update(dict(Password=enc_password, AppKey=enc_appkey))

	res = make_post_request(endpoint, headers=headers, data=json.dumps({ 'data': payload }))
	handle_err_response(res)

	auth_token, token_expiry, sek = extract_token_and_sek(res, appkey)

	einv_creds.auth_token = auth_token
	einv_creds.token_expiry = get_datetime(token_expiry)
	einv_creds.sek = sek
	einv_creds.save()

def extract_token_and_sek(response, appkey):
	data = response.get('Data')
	auth_token = data.get('AuthToken')
	token_expiry = data.get('TokenExpiry')
	enc_sek = data.get('Sek')
	sek = aes_decrypt(enc_sek, appkey)
	return auth_token, token_expiry, sek

def attach_signed_invoice(doctype, name, data):
	f = frappe.get_doc({
		"doctype": "File",
		"file_name": name + "e_invoice.json",
		"attached_to_doctype": doctype,
		"attached_to_name": name,
		"content": json.dumps(data),
		"is_private": True
	}).insert()

def get_gstin_details(gstin):
	einv_creds = get_einv_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eivital/v1.03/Master/gstin/{gstin}'.format(gstin=gstin)
	headers = get_header(einv_creds)

	res = make_get_request(endpoint, headers=headers)
	handle_err_response(res)

	enc_json = res.get('Data')
	json_str = aes_decrypt(enc_json, einv_creds.sek)
	data = json.loads(json_str)

	return data

@frappe.whitelist()
def generate_irn(doctype, name):
	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice'
	einv_creds = get_einv_credentials()
	headers = get_header(einv_creds)

	e_invoice = make_e_invoice(doctype, name)

	enc_e_invoice_json = aes_encrypt(e_invoice, einv_creds.sek)
	payload = dict(Data=enc_e_invoice_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	res = handle_err_response(res)

	enc_json = res.get('Data')
	json_str = aes_decrypt(enc_json, einv_creds.sek)

	signed_einvoice = json.loads(json_str)
	handle_irn_response(signed_einvoice)

	update_einvoice_fields(doctype, name, signed_einvoice)

	attach_qrcode_image(doctype, name)
	attach_signed_invoice(doctype, name, signed_einvoice['DecryptedSignedInvoice'])

	return signed_einvoice

def get_irn_details(irn):
	einv_creds = get_einv_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/irn/{irn}'.format(irn=irn)
	headers = get_header(einv_creds)

	res = make_get_request(endpoint, headers=headers)
	handle_err_response(res)

	return res

@frappe.whitelist()
def cancel_irn(doctype, name, irn, reason, remark=''):
	einv_creds = get_einv_credentials()

	endpoint = 'https://einv-apisandbox.nic.in/eicore/v1.03/Invoice/Cancel'
	headers = get_header(einv_creds)

	cancel_e_inv = json.dumps(dict(Irn=irn, CnlRsn=reason, CnlRem=remark))
	enc_json = aes_encrypt(cancel_e_inv, einv_creds.sek)
	payload = dict(Data=enc_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	handle_err_response(res)

	frappe.db.set_value(doctype, name, 'irn_cancelled', 1)

	return res

@frappe.whitelist()
def cancel_eway_bill(eway_bill, reason, remark=''):
	einv_creds = get_einv_credentials()
	endpoint = 'https://einv-apisandbox.nic.in/ewaybillapi/v1.03/ewayapi'
	headers = get_header(einv_creds)

	cancel_eway_bill_json = json.dumps(dict(ewbNo=eway_bill, cancelRsnCode=reason, cancelRmrk=remark))
	enc_json = aes_encrypt(cancel_eway_bill_json, einv_creds.sek)
	payload = dict(action="CANEWB", Data=enc_json)

	res = make_post_request(endpoint, headers=headers, data=json.dumps(payload))
	handle_err_response(res)

	return res

def handle_irn_response(data):
	enc_signed_invoice = data['SignedInvoice']
	enc_signed_qr_code = data['SignedQRCode']
	signed_invoice = jwt_decrypt(enc_signed_invoice)['data']
	signed_qr_code = jwt_decrypt(enc_signed_qr_code)['data']
	data['DecryptedSignedInvoice'] = json.loads(signed_invoice)
	data['DecryptedSignedQRCode'] = json.loads(signed_qr_code)

def handle_err_response(response):
	if response.get('Status') == 0:
		err_details = response.get('ErrorDetails')
		print(response)
		err_msg = ""
		for d in err_details:
			err_code = d.get('ErrorCode')
			if err_code == '2150':
				irn = [d['Desc']['Irn'] for d in response.get('InfoDtls') if d['InfCd'] == 'DUPIRN']
				response = get_irn_details(irn[0])
				return response

			err_msg += d.get('ErrorMessage')
			err_msg += "<br>"
		frappe.throw(_(err_msg), title=_('API Request Failed'))

	return response

def read_json(name):
	file_path = os.path.join(os.path.dirname(__file__), "{name}.json".format(name=name))
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

	return frappe._dict(dict(
		invoice_type=invoice_type, invoice_name=invoice_name, invoice_date=invoice_date
	))

def get_party_gstin_details(party_address):
	address = frappe.get_all("Address", filters={"name": party_address}, fields=["*"])[0]

	gstin = address.get('gstin')
	gstin_details = get_gstin_details(gstin)
	legal_name = gstin_details.get('LegalName')
	trade_name = gstin_details.get('TradeName')
	location = gstin_details.get('AddrLoc')
	state_code = gstin_details.get('StateCode')
	pincode = cint(gstin_details.get('AddrPncd'))
	address_line1 = "{} {}".format(gstin_details.get('AddrBno'), gstin_details.get('AddrFlno'))
	address_line2 = "{} {}".format(gstin_details.get('AddrBnm'), gstin_details.get('AddrSt'))
	email_id = address.get('email_id')
	phone = address.get('phone')
	if state_code == 97:
		pincode = 999999

	return frappe._dict(dict(
		gstin=gstin, legal_name=legal_name, location=location,
		pincode=pincode, state_code=state_code, address_line1=address_line1,
		address_line2=address_line2, email=email_id, phone=phone
	))

def get_overseas_address_details(party_address):
	address_title, address_line1, address_line2, city, phone, email_id = frappe.db.get_value(
		"Address", party_address, ["address_title", "address_line1", "address_line2", "city", "phone", "email_id"]
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
		item_schema = read_json("einv_item_template")
		item = frappe._dict(dict())
		item.update(d.as_dict())
		item.sr_no = d.idx
		item.description = d.item_name
		item.is_service_item = "N" if frappe.db.get_value("Item", d.item_code, "is_stock_item") else "Y"
		item.batch_expiry_date = frappe.db.get_value("Batch", d.batch_no, "expiry_date") if d.batch_no else None
		item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
		item.unit_rate = item.base_price_list_rate if item.discount_amount else item.base_rate
		item.total_amount = item.unit_rate * item.qty
		item.discount_amount = item.discount_amount * item.qty
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

def get_value_details(invoice):
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

def get_payment_details(invoice):
	payee_name = invoice.company
	mode_of_payment = ", ".join([d.mode_of_payment for d in invoice.payments])
	paid_amount = invoice.base_paid_amount
	outstanding_amount = invoice.outstanding_amount

	return frappe._dict(dict(
		payee_name=payee_name, mode_of_payment=mode_of_payment,
		paid_amount=paid_amount, outstanding_amount=outstanding_amount
	))

def get_return_doc_reference(invoice):
	invoice_date = frappe.db.get_value("Sales Invoice", invoice.return_against, "posting_date")
	return frappe._dict(dict(
		invoice_name=invoice.return_against, invoice_date=invoice_date
	))

def get_eway_bill_details(invoice):
	if not invoice.distance:
		frappe.throw(_("Distance is mandatory for E-Way Bill generation"), title=_("Missing Values"))

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
def make_e_invoice(doctype, name):
	invoice = frappe.get_doc(doctype, name)
	schema = read_json("einv_template")
	validations = json.loads(read_json("einv_validation"))

	trans_details = get_trans_details(invoice)
	doc_details = get_doc_details(invoice)
	seller_details = get_party_gstin_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_gstin_details(invoice.customer_address)
		place_of_supply = invoice.place_of_supply.split('-')[0]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	item_list = get_item_list(invoice)
	value_details = get_value_details(invoice)
	
	shipping_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		shipping_details = get_party_gstin_details(invoice.shipping_address_name)
	
	payment_details = frappe._dict({})
	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)
	
	prev_doc_details = frappe._dict({})
	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)
	
	dispatch_details = frappe._dict({})
	period_details = frappe._dict({})
	export_details = frappe._dict({})
	eway_bill_details = frappe._dict({})
	if invoice.transporter:
		eway_bill_details = get_eway_bill_details(invoice)

	e_invoice = schema.format(
		trans_details=trans_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, value_details=value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)
	e_invoice = json.loads(e_invoice)

	error_msgs = validate_einvoice(validations, e_invoice, [])
	if error_msgs:
		if len(error_msgs) > 1:
			li = ["<li>"+ d +"</li>" for d in error_msgs]
			frappe.throw(_("""<ul style="padding-left: 20px">{}</ul>""").format("".join(li)), title=_("E Invoice Validation Failed"))
		else:
			frappe.throw(_("{}").format(error_msgs[0]), title=_("E Invoice Validation Failed"))

	return {'einvoice': json.dumps([e_invoice])}

def validate_einvoice(validations, e_invoice, error_msgs=[]):
	type_map = {
		"string": cstr,
		"number": cint,
		"object": dict,
		"array": list
	}
	
	for field, value in validations.items():
		if isinstance(value, list): value = value[0]

		invoice_value = e_invoice.get(field)
		if not invoice_value:
			continue

		should_be_of_type = type_map[value.get('type').lower()]
		if should_be_of_type == dict:
			properties = value.get('properties')

			if isinstance(invoice_value, list):
				for d in invoice_value:
					validate_einvoice(properties, d, error_msgs)
			else:
				validate_einvoice(properties, invoice_value, error_msgs)
				# remove keys with empty dicts
				if not invoice_value:
					e_invoice.pop(field, None)
			continue
		
		if invoice_value == "None":
			# remove keys with empty values
			e_invoice.pop(field, None)
			continue
		
		# convert to int or str
		e_invoice[field] = should_be_of_type(invoice_value)
		
		should_be_of_len = value.get('maxLength')
		should_be_greater_than = flt(value.get('minimum'))
		should_be_less_than = flt(value.get('maximum'))
		pattern_str = value.get('pattern')
		pattern = re.compile(pattern_str or "")

		field_label = value.get("label") or field

		if value.get('type').lower() == 'string' and len(invoice_value) > should_be_of_len:
			error_msgs.append("{} should not exceed {} characters".format(field_label, should_be_of_len))
		if value.get('type').lower() == 'number' and not (flt(invoice_value) <= should_be_less_than):
			error_msgs.append("{} should be less than {}".format(field_label, should_be_less_than))
		if pattern_str and not pattern.match(invoice_value):
			error_msgs.append(value.get('validationMsg'))
	
	return error_msgs

def update_einvoice_fields(doctype, name, signed_einvoice):
	enc_signed_invoice = signed_einvoice.get('SignedInvoice')
	decrypted_signed_invoice = jwt_decrypt(enc_signed_invoice)['data']

	frappe.db.set_value(doctype, name, 'irn', signed_einvoice.get('Irn'))
	frappe.db.set_value(doctype, name, 'ewaybill', signed_einvoice.get('EwbNo'))
	frappe.db.set_value(doctype, name, 'signed_qr_code', signed_einvoice.get('SignedQRCode').split('.')[1])
	frappe.db.set_value(doctype, name, 'signed_einvoice', decrypted_signed_invoice)

@frappe.whitelist()
def download_einvoice():
	data = frappe._dict(frappe.local.form_dict)
	einvoice = data['einvoice']
	name = data['name']

	frappe.response['filename'] = "E-Invoice-" + name + ".json"
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

@frappe.whitelist()
def download_cancel_einvoice():
	data = frappe._dict(frappe.local.form_dict)
	name = data['name']
	irn = data['irn']
	reason = data['reason']
	remark = data['remark']

	cancel_einvoice = json.dumps([dict(Irn=irn, CnlRsn=reason, CnlRem=remark)])

	frappe.response['filename'] = "Cancel E-Invoice " + name + ".json"
	frappe.response['filecontent'] = cancel_einvoice
	frappe.response['content_type'] = 'application/json'
	frappe.response['type'] = 'download'

@frappe.whitelist()
def upload_cancel_ack():
	cancel_ack = json.loads(frappe.local.uploaded_file)
	data = frappe._dict(frappe.local.form_dict)
	doctype = data['doctype']
	name = data['docname']

	frappe.db.set_value(doctype, name, "irn_cancelled", 1)

def attach_qrcode_image(doctype, name):
	qrcode = frappe.db.get_value(doctype, name, 'signed_qr_code')

	if not qrcode: return

	_file = frappe.get_doc({
		"doctype": "File",
		"file_name": "Signed_QR_{name}.png".format(name=name),
		"attached_to_doctype": doctype,
		"attached_to_name": name,
		"attached_to_field": "qrcode_image",
		"content": "qrcode"
	})
	_file.save()
	frappe.db.commit()
	url = qrcreate(qrcode)
	abs_file_path = os.path.abspath(_file.get_full_path())
	url.png(abs_file_path, scale=2)

	frappe.db.set_value(doctype, name, 'qrcode_image', _file.file_url)