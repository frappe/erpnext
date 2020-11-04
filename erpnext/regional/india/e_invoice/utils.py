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
			msg = _('As you have E-Invoicing enabled, To be able to generate IRN for this invoice, ')
			msg += _('document name {} exceed 16 letters. ').format(bold(_('should not')))
			msg += '<br><br>'
			msg += _('You must {} your {} in order to have document name of {} length 16. ').format(
				bold(_('modify')), bold(_('naming series')), bold(_('maximum'))
			)
			msg += _('Please account for ammended document names too. ')
			frappe.throw(msg, title=title)

	elif doc.docstatus == 1 and doc._action == 'submit' and not doc.irn:
		frappe.throw(_('You must generate IRN before submitting the document.'), title=_('Missing IRN'))

	elif doc.docstatus == 2 and doc._action == 'cancel' and not doc.irn_cancelled:
		frappe.throw(_('You must cancel IRN before cancelling the document.'), title=_('Cancel Not Allowed'))

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
		rr, sez, overseas, export = bold('Registered Regular'), bold('SEZ'), bold('Overseas'), bold('Deemed Export')
		frappe.throw(
			_('GST category should be one of {}, {}, {}, {}').format(rr, sez, overseas, export),
			title=_('Invalid Supply Type')
		)

	return frappe._dict(dict(
		tax_scheme='GST',
		supply_type=supply_type,
		reverse_charge=invoice.reverse_charge
	))

def get_doc_details(invoice):
	if invoice.doctype == 'Purchase Invoice' and invoice.is_return:
		invoice_type = 'DBN'
	else:
		invoice_type = 'CRN' if invoice.is_return else 'INV'

	invoice_name = invoice.name
	invoice_date = format_date(invoice.posting_date, 'dd/mm/yyyy')

	return frappe._dict(dict(
		invoice_type=invoice_type,
		invoice_name=invoice_name,
		invoice_date=invoice_date
	))

def get_party_details(address_name):
	address = frappe.get_all('Address', filters={'name': address_name}, fields=['*'])[0]
	gstin = address.get('gstin')

	gstin_details = GSPConnector.get_gstin_details(gstin)
	legal_name = gstin_details.get('LegalName')
	trade_name = gstin_details.get('TradeName')
	location = gstin_details.get('AddrLoc') or address.get('city')
	state_code = gstin_details.get('StateCode')
	pincode = gstin_details.get('AddrPncd')
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
		item.unit_rate = abs(item.base_price_list_rate) if item.discount_amount else abs(item.base_net_rate)
		item.gross_amount = abs(item.unit_rate * item.qty)
		item.discount_amount = abs(item.discount_amount * item.qty)
		item.taxable_value = abs(item.base_net_amount)
		item.tax_rate = item.cess_rate = item.other_charges = 0
		item.cgst_amount = item.sgst_amount = item.igst_amount = item.cess_amount = 0
		for t in invoice.taxes:
			item_tax_detail = json.loads(t.item_wise_tax_detail).get(item.item_code)
			if t.account_head in gst_accounts_list:
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
		
		item.total_value = abs(
			item.base_amount + item.igst_amount + item.sgst_amount +
			item.cgst_amount + item.cess_amount + item.other_charges
		)
		einv_item = item_schema.format(item=item)
		item_list.append(einv_item)

	return ', '.join(item_list)

def get_value_details(invoice):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	value_details = frappe._dict(dict())
	value_details.base_net_total = abs(invoice.base_net_total)
	value_details.invoice_discount_amt = invoice.discount_amount if invoice.discount_amount > 0 else 0
	value_details.round_off = invoice.rounding_adjustment - (invoice.discount_amount if invoice.discount_amount < 0 else 0)
	value_details.base_grand_total = abs(invoice.base_rounded_total)
	value_details.grand_total = abs(invoice.rounded_total)
	value_details.total_cgst_amt = 0
	value_details.total_sgst_amt = 0
	value_details.total_igst_amt = 0
	value_details.total_cess_amt = 0
	value_details.total_other_charges = 0
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
		else:
			value_details.total_other_charges += abs(t.base_tax_amount_after_discount_amount)
	
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
	if invoice.is_return:
		frappe.throw(_('E-Way Bill cannot be generated for Credit Notes & Debit Notes'), title=_('E Invoice Validation Failed'))

	mode_of_transport = { 'Road': '1', 'Air': '2', 'Rail': '3', 'Ship': '4' }
	vehicle_type = { 'Regular': 'R', 'Over Dimensional Cargo (ODC)': 'O' }

	return frappe._dict(dict(
		gstin=invoice.gst_transporter_id,
		name=invoice.transporter_name,
		mode_of_transport=mode_of_transport[invoice.mode_of_transport],
		distance=invoice.distance or 0,
		document_name=invoice.lr_no,
		document_date=format_date(invoice.lr_date, 'dd/mm/yyyy'),
		vehicle_no=invoice.vehicle_no,
		vehicle_type=vehicle_type[invoice.gst_vehicle_type]
	))

@frappe.whitelist()
def make_einvoice(doctype, name):
	invoice = frappe.get_doc(doctype, name)
	schema = read_json('einv_template')

	trans_details = get_trans_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	value_details = get_value_details(invoice)
	trans_details = get_trans_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, doctype) or invoice.billing_address_gstin
		place_of_supply = place_of_supply[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))
	
	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		shipping_details = get_party_details(invoice.shipping_address_name)
	
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
	errors = validate_einvoice(validations, einvoice)
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
			is_integer = '.' not in str(field_validation.get('maximum'))
			einvoice[fieldname] = flt(value, 2) if not is_integer else cint(value)
			value = einvoice[fieldname]

		max_length = field_validation.get('maxLength')
		minimum = flt(field_validation.get('minimum'))
		maximum = flt(field_validation.get('maximum'))
		pattern_str = field_validation.get('pattern')
		pattern = re.compile(pattern_str or '')

		label = field_validation.get('description') or fieldname

		if value_type == 'string' and len(value) > max_length:
			errors.append(_('{} should not exceed {} characters').format(label, max_length))
		if value_type == 'number' and (value > maximum or value < minimum):
			errors.append(_('{} {} should be between {} and {}').format(label, value, minimum, maximum))
		if pattern_str and not pattern.match(value):
			errors.append(field_validation.get('validationMsg'))
	
	return errors

def update_invoice(doctype, docname, res):
	enc_signed_invoice = res.get('SignedInvoice')
	dec_signed_invoice = jwt.decode(enc_signed_invoice, verify=False)['data']

	frappe.db.set_value(doctype, docname, 'irn', res.get('Irn'))
	frappe.db.set_value(doctype, docname, 'ewaybill', res.get('EwbNo'))
	frappe.db.set_value(doctype, docname, 'signed_einvoice', dec_signed_invoice)

	signed_qr_code = res.get('SignedQRCode')
	frappe.db.set_value(doctype, docname, 'signed_qr_code', signed_qr_code)

	attach_qrcode_image(doctype, docname, signed_qr_code)

def attach_qrcode_image(doctype, docname, qrcode):
	if not qrcode: return

	_file = frappe.new_doc('File')
	_file.update({
		'file_name': f'QRCode_{docname}.png',
		'attached_to_doctype': doctype,
		'attached_to_name': docname,
		'content': 'qrcode',
		'is_private': 1
	})
	_file.insert()
	frappe.db.commit()
	url = qrcreate(qrcode)
	abs_file_path = os.path.abspath(_file.get_full_path())
	url.png(abs_file_path, scale=2)

	frappe.db.set_value(doctype, docname, 'qrcode_image', _file.file_url)

class GSPConnector():
	def __init__(self):
		self.credentials = frappe.get_cached_doc('E Invoice Settings')

		self.base_url = 'https://gsp.adaequare.com/'
		self.authenticate_url = self.base_url + 'gsp/authenticate?grant_type=token'
		self.gstin_details_url = self.base_url + 'test/enriched/ei/api/master/gstin'
		self.generate_irn_url = self.base_url + 'test/enriched/ei/api/invoice'
		self.cancel_irn_url = self.base_url + 'test/enriched/ei/api/invoice/cancel'
		self.cancel_ewaybill_url = self.base_url + '/test/enriched/ei/api/ewayapi'
	
	def get_auth_token(self):
		if time_diff_in_seconds(self.credentials.token_expiry, now_datetime()) < 150.0:
			self.fetch_auth_token()
		
		return self.credentials.auth_token

	def fetch_auth_token(self):
		headers = {
			'gspappid': self.credentials.client_id,
			'gspappsecret': self.credentials.client_secret
		}

		try:
			res = make_post_request(self.authenticate_url, headers=headers)
			self.credentials.auth_token = "{} {}".format(res.get('token_type'), res.get('access_token'))
			self.credentials.token_expiry = add_to_date(None, seconds=res.get('expires_in'))
			self.credentials.save()

		except Exception as e:
			self.log_error(e)
			raise
	
	def get_headers(self):
		return {
			'content-type': 'application/json',
			'user_name': self.credentials.username,
			'password': self.credentials.get_password(),
			'gstin': self.credentials.gstin,
			'authorization': self.get_auth_token(),
			'requestid': str(base64.b64encode(os.urandom(18))),
		}
	
	def fetch_gstin_details(self, gstin):
		headers = self.get_headers()

		try:
			params = '?gstin={gstin}'.format(gstin=gstin)
			res = make_get_request(self.gstin_details_url + params, headers=headers)
			if res.get('success'):
				return res.get('result')

		except Exception as e:
			self.log_error(e)
		
		return {}
	
	@staticmethod
	def get_gstin_details(gstin):
		'''fetch or get cached GSTIN details'''

		if not hasattr(frappe.local, 'gstin_cache'):
			frappe.local.gstin_cache = {}

		key = gstin
		details = frappe.local.gstin_cache.get(key)
		if details:
			return details

		details = frappe.cache().hget('gstin_cache', key)
		if details:
			frappe.local.gstin_cache[key] = details
			return details
		
		gsp_connector = GSPConnector()
		details = gsp_connector.fetch_gstin_details(gstin)

		frappe.local.gstin_cache[key] = details
		frappe.cache().hset('gstin_cache', key, details)
		return details

	def generate_irn(self, docname):
		headers = self.get_headers()
		doctype = 'Sales Invoice'
		einvoice = make_einvoice(doctype, docname)
		data = json.dumps(einvoice)

		try:
			res = make_post_request(self.generate_irn_url, headers=headers, data=data)
			if res.get('success'):
				update_invoice(doctype, docname, res.get('result'))
			else:
				# {'success': False, 'message': '3039 : Seller Details:Pincode-560009 does not belong to the state-1, 2177 : Invalid item unit code(s)-UNIT'}
				self.log_error(res)

		except Exception as e:
			self.log_error(e)
	
	def cancel_irn(self, docname, irn, reason, remark):
		headers = self.get_headers()
		doctype = 'Sales Invoice'
		data = json.dumps({
			'Irn': irn,
			'Cnlrsn': reason,
			'Cnlrem': remark
		})

		try:
			res = make_post_request(self.cancel_irn_url, headers=headers, data=data)
			if res.get('success'):
				frappe.db.set_value(doctype, docname, 'irn_cancelled', 1)
				# frappe.db.set_value(doctype, docname, 'cancelled_on', res.get('CancelDate'))

		except Exception as e:
			self.log_error(e)
	
	def cancel_eway_bill(self, docname, eway_bill, reason, remark):
		headers = self.get_headers()
		doctype = 'Sales Invoice'
		data = json.dumps({
			'ewbNo': eway_bill,
			'cancelRsnCode': reason,
			'cancelRmrk': remark
		})

		try:
			res = make_post_request(self.cancel_ewaybill_url, headers=headers, data=data)
			if res.get('success'):
				frappe.db.set_value(doctype, docname, 'ewaybill', '')
				frappe.db.set_value(doctype, docname, 'eway_bill_cancelled', 1)

		except Exception as e:
			self.log_error(e)

	def log_error(self, exc):
		print(exc)

@frappe.whitelist()
def generate_irn(docname):
	gsp_connector = GSPConnector()
	gsp_connector.generate_irn(docname)

@frappe.whitelist()
def cancel_irn(docname, irn, reason, remark):
	gsp_connector = GSPConnector()
	gsp_connector.cancel_irn(docname, irn, reason, remark)