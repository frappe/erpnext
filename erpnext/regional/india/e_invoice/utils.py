# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import re
import jwt
import sys
import json
import base64
import frappe
import six
import traceback
import io
from frappe import _, bold
from pyqrcode import create as qrcreate
from frappe.integrations.utils import make_post_request, make_get_request
from erpnext.regional.india.utils import get_gst_accounts, get_place_of_supply
from frappe.utils.data import cstr, cint, format_date, flt, time_diff_in_seconds, now_datetime, add_to_date, get_link_to_form

def validate_einvoice_fields(doc):
	einvoicing_enabled = cint(frappe.db.get_value('E Invoice Settings', 'E Invoice Settings', 'enable'))
	invalid_doctype = doc.doctype != 'Sales Invoice'
	invalid_supply_type = doc.get('gst_category') not in ['Registered Regular', 'SEZ', 'Overseas', 'Deemed Export']
	company_transaction = doc.get('billing_address_gstin') == doc.get('company_gstin')
	no_taxes_applied = not doc.get('taxes')

	if not einvoicing_enabled or invalid_doctype or invalid_supply_type or company_transaction or no_taxes_applied:
		return

	if doc.docstatus == 0 and doc._action == 'save':
		if doc.irn:
			frappe.throw(_('You cannot edit the invoice after generating IRN'), title=_('Edit Not Allowed'))
		if len(doc.name) > 16:
			raise_document_name_too_long_error()

	elif doc.docstatus == 1 and doc._action == 'submit' and not doc.irn:
		frappe.throw(_('You must generate IRN before submitting the document.'), title=_('Missing IRN'))

	elif doc.irn and doc.docstatus == 2 and doc._action == 'cancel' and not doc.irn_cancelled:
		frappe.throw(_('You must cancel IRN before cancelling the document.'), title=_('Cancel Not Allowed'))

def raise_document_name_too_long_error():
	title = _('Document ID Too Long')
	msg = _('As you have E-Invoicing enabled, to be able to generate IRN for this invoice, ')
	msg += _('document id {} exceed 16 letters. ').format(bold(_('should not')))
	msg += '<br><br>'
	msg += _('You must {} your {} in order to have document id of {} length 16. ').format(
		bold(_('modify')), bold(_('naming series')), bold(_('maximum'))
	)
	msg += _('Please account for ammended documents too. ')
	frappe.throw(msg, title=title)

def read_json(name):
	file_path = os.path.join(os.path.dirname(__file__), '{name}.json'.format(name=name))
	with open(file_path, 'r') as f:
		return cstr(f.read())

def get_transaction_details(invoice):
	supply_type = ''
	if invoice.gst_category == 'Registered Regular': supply_type = 'B2B'
	elif invoice.gst_category == 'SEZ': supply_type = 'SEZWOP'
	elif invoice.gst_category == 'Overseas': supply_type = 'EXPWOP'
	elif invoice.gst_category == 'Deemed Export': supply_type = 'DEXP'

	if not supply_type:
		rr, sez, overseas, export = bold('Registered Regular'), bold('SEZ'), bold('Overseas'), bold('Deemed Export')
		frappe.throw(_('GST category should be one of {}, {}, {}, {}').format(rr, sez, overseas, export),
			title=_('Invalid Supply Type'))

	return frappe._dict(dict(
		tax_scheme='GST',
		supply_type=supply_type,
		reverse_charge=invoice.reverse_charge
	))

def get_doc_details(invoice):
	invoice_type = 'CRN' if invoice.is_return else 'INV'

	invoice_name = invoice.name
	invoice_date = format_date(invoice.posting_date, 'dd/mm/yyyy')

	return frappe._dict(dict(
		invoice_type=invoice_type,
		invoice_name=invoice_name,
		invoice_date=invoice_date
	))

def get_party_details(address_name):
	d = frappe.get_all('Address', filters={'name': address_name}, fields=['*'])[0]

	if (not d.gstin
		or not d.city
		or not d.pincode
		or not d.address_title
		or not d.address_line1
		or not d.gst_state_number):

		frappe.throw(
			msg=_('Address lines, city, pincode, gstin is mandatory for address {}. Please set them and try again.').format(
				get_link_to_form('Address', address_name)
			),
			title=_('Missing Address Fields')
		)

	if d.gst_state_number == 97:
		# according to einvoice standard
		pincode = 999999

	return frappe._dict(dict(
		gstin=d.gstin,
		legal_name=sanitize_for_json(d.address_title),
		location=sanitize_for_json(d.city),
		pincode=d.pincode,
		state_code=d.gst_state_number,
		address_line1=sanitize_for_json(d.address_line1),
		address_line2=sanitize_for_json(d.address_line2)
	))

def get_gstin_details(gstin):
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

	if not details:
		return GSPConnector.get_gstin_details(gstin)

def get_overseas_address_details(address_name):
	address_title, address_line1, address_line2, city = frappe.db.get_value(
		'Address', address_name, ['address_title', 'address_line1', 'address_line2', 'city']
	)

	if not address_title or not address_line1 or not city:
		frappe.throw(
			msg=_('Address lines and city is mandatory for address {}. Please set them and try again.').format(
				get_link_to_form('Address', address_name)
			),
			title=_('Missing Address Fields')
		)

	return frappe._dict(dict(
		gstin='URP',
		legal_name=sanitize_for_json(address_title),
		location=city,
		address_line1=sanitize_for_json(address_line1),
		address_line2=sanitize_for_json(address_line2),
		pincode=999999, state_code=96, place_of_supply=96
	))

def get_item_list(invoice):
	item_list = []

	for d in invoice.items:
		einvoice_item_schema = read_json('einv_item_template')
		item = frappe._dict({})
		item.update(d.as_dict())

		item.sr_no = d.idx
		item.description = sanitize_for_json(d.item_name)

		item.qty = abs(item.qty)
		item.discount_amount = 0
		item.unit_rate = abs(item.base_net_amount / item.qty)
		item.gross_amount = abs(item.base_net_amount)
		item.taxable_value = abs(item.base_net_amount)

		item.batch_expiry_date = frappe.db.get_value('Batch', d.batch_no, 'expiry_date') if d.batch_no else None
		item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
		item.is_service_item = 'N' if frappe.db.get_value('Item', d.item_code, 'is_stock_item') else 'Y'
		item.serial_no = ""

		item = update_item_taxes(invoice, item)

		item.total_value = abs(
			item.taxable_value + item.igst_amount + item.sgst_amount +
			item.cgst_amount + item.cess_amount + item.cess_nadv_amount + item.other_charges
		)
		einv_item = einvoice_item_schema.format(item=item)
		item_list.append(einv_item)

	return ', '.join(item_list)

def update_item_taxes(invoice, item):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	for attr in [
		'tax_rate', 'cess_rate', 'cess_nadv_amount',
		'cgst_amount',  'sgst_amount', 'igst_amount',
		'cess_amount', 'cess_nadv_amount', 'other_charges'
		]:
		item[attr] = 0

	for t in invoice.taxes:
		is_applicable = t.tax_amount and t.account_head in gst_accounts_list
		if is_applicable:
			# this contains item wise tax rate & tax amount (incl. discount)
			item_tax_detail = json.loads(t.item_wise_tax_detail).get(item.item_code)

			item_tax_rate = item_tax_detail[0]
			# item tax amount excluding discount amount
			item_tax_amount = (item_tax_rate / 100) * item.base_net_amount

			if t.account_head in gst_accounts.cess_account:
				item_tax_amount_after_discount = item_tax_detail[1]
				if t.charge_type == 'On Item Quantity':
					item.cess_nadv_amount += abs(item_tax_amount_after_discount)
				else:
					item.cess_rate += item_tax_rate
					item.cess_amount += abs(item_tax_amount_after_discount)

			for tax_type in ['igst', 'cgst', 'sgst']:
				if t.account_head in gst_accounts[f'{tax_type}_account']:
					item.tax_rate += item_tax_rate
					item[f'{tax_type}_amount'] += abs(item_tax_amount)

	return item

def get_invoice_value_details(invoice):
	invoice_value_details = frappe._dict(dict())

	if invoice.apply_discount_on == 'Net Total' and invoice.discount_amount:
		invoice_value_details.base_total = abs(invoice.base_total)
		invoice_value_details.invoice_discount_amt = abs(invoice.base_discount_amount)
	else:
		invoice_value_details.base_total = abs(invoice.base_net_total)
		# since tax already considers discount amount
		invoice_value_details.invoice_discount_amt = 0

	invoice_value_details.round_off = invoice.base_rounding_adjustment
	invoice_value_details.base_grand_total = abs(invoice.base_rounded_total) or abs(invoice.base_grand_total)
	invoice_value_details.grand_total = abs(invoice.rounded_total) or abs(invoice.grand_total)

	invoice_value_details = update_invoice_taxes(invoice, invoice_value_details)

	return invoice_value_details

def update_invoice_taxes(invoice, invoice_value_details):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	invoice_value_details.total_cgst_amt = 0
	invoice_value_details.total_sgst_amt = 0
	invoice_value_details.total_igst_amt = 0
	invoice_value_details.total_cess_amt = 0
	invoice_value_details.total_other_charges = 0
	for t in invoice.taxes:
		if t.account_head in gst_accounts_list:
			if t.account_head in gst_accounts.cess_account:
				# using after discount amt since item also uses after discount amt for cess calc
				invoice_value_details.total_cess_amt += abs(t.base_tax_amount_after_discount_amount)

			for tax_type in ['igst', 'cgst', 'sgst']:
				if t.account_head in gst_accounts[f'{tax_type}_account']:
					invoice_value_details[f'total_{tax_type}_amt'] += abs(t.base_tax_amount_after_discount_amount)
		else:
			invoice_value_details.total_other_charges += abs(t.base_tax_amount_after_discount_amount)

	return invoice_value_details

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

	mode_of_transport = { '': '', 'Road': '1', 'Air': '2', 'Rail': '3', 'Ship': '4' }
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

def validate_mandatory_fields(invoice):
	if not invoice.company_address:
		frappe.throw(_('Company Address is mandatory to fetch company GSTIN details.'), title=_('Missing Fields'))
	if not invoice.customer_address:
		frappe.throw(_('Customer Address is mandatory to fetch customer GSTIN details.'), title=_('Missing Fields'))
	if not frappe.db.get_value('Address', invoice.company_address, 'gstin'):
		frappe.throw(
			_('GSTIN is mandatory to fetch company GSTIN details. Please enter GSTIN in selected company address.'),
			title=_('Missing Fields')
		)
	if invoice.gst_category != 'Overseas' and not frappe.db.get_value('Address', invoice.customer_address, 'gstin'):
		frappe.throw(
			_('GSTIN is mandatory to fetch customer GSTIN details. Please enter GSTIN in selected customer address.'),
			title=_('Missing Fields')
		)

def make_einvoice(invoice):
	validate_mandatory_fields(invoice)

	schema = read_json('einv_template')

	transaction_details = get_transaction_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	invoice_value_details = get_invoice_value_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, invoice.doctype) or sanitize_for_json(invoice.billing_address_gstin)
		place_of_supply = place_of_supply[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		if invoice.gst_category == 'Overseas':
			shipping_details = get_overseas_address_details(invoice.shipping_address_name)
		else:
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
		transaction_details=transaction_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, invoice_value_details=invoice_value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)
	einvoice = safe_json_load(einvoice)

	validations = json.loads(read_json('einv_validation'))
	errors = validate_einvoice(validations, einvoice)
	if errors:
		message = "\n".join([
			"E Invoice: ", json.dumps(einvoice, indent=4),
			"-" * 50,
			"Errors: ", json.dumps(errors, indent=4)
		])
		frappe.log_error(title="E Invoice Validation Failed", message=message)
		frappe.throw(errors, title=_('E Invoice Validation Failed'), as_list=1)

	return einvoice

def safe_json_load(json_string):
	JSONDecodeError = ValueError if six.PY2 else json.JSONDecodeError

	try:
		return json.loads(json_string)
	except JSONDecodeError as e:
		# print a snippet of 40 characters around the location where error occured
		pos = e.pos
		start, end = max(0, pos-20), min(len(json_string)-1, pos+20)
		snippet = json_string[start:end]
		frappe.throw(_("Error in input data. Please check for any special characters near following input: <br> {}").format(snippet))

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
			precision = 3 if '.999' in str(field_validation.get('maximum')) else 2
			einvoice[fieldname] = flt(value, precision) if not is_integer else cint(value)
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

class RequestFailed(Exception): pass

class GSPConnector():
	def __init__(self, doctype=None, docname=None):
		self.e_invoice_settings = frappe.get_cached_doc('E Invoice Settings')
		sandbox_mode = self.e_invoice_settings.sandbox_mode

		self.invoice = frappe.get_cached_doc(doctype, docname) if doctype and docname else None
		self.credentials = self.get_credentials()

		# authenticate url is same for sandbox & live
		self.authenticate_url = 'https://gsp.adaequare.com/gsp/authenticate?grant_type=token'
		self.base_url = 'https://gsp.adaequare.com' if not sandbox_mode else 'https://gsp.adaequare.com/test'

		self.cancel_irn_url = self.base_url + '/enriched/ei/api/invoice/cancel'
		self.irn_details_url = self.base_url + '/enriched/ei/api/invoice/irn'
		self.generate_irn_url = self.base_url + '/enriched/ei/api/invoice'
		self.gstin_details_url = self.base_url + '/enriched/ei/api/master/gstin'
		self.cancel_ewaybill_url = self.base_url + '/enriched/ewb/ewayapi?action=CANEWB'
		self.generate_ewaybill_url = self.base_url + '/enriched/ei/api/ewaybill'

	def get_credentials(self):
		if self.invoice:
			gstin = self.get_seller_gstin()
			if not self.e_invoice_settings.enable:
				frappe.throw(_("E-Invoicing is disabled. Please enable it from {} to generate e-invoices.").format(get_link_to_form("E Invoice Settings", "E Invoice Settings")))
			credentials = next(d for d in self.e_invoice_settings.credentials if d.gstin == gstin)
		else:
			credentials = self.e_invoice_settings.credentials[0] if self.e_invoice_settings.credentials else None
		return credentials

	def get_seller_gstin(self):
		gstin = self.invoice.company_gstin or frappe.db.get_value('Address', self.invoice.company_address, 'gstin')
		if not gstin:
			frappe.throw(_('Cannot retrieve Company GSTIN. Please select company address with valid GSTIN.'))
		return gstin

	def get_auth_token(self):
		if time_diff_in_seconds(self.e_invoice_settings.token_expiry, now_datetime()) < 150.0:
			self.fetch_auth_token()

		return self.e_invoice_settings.auth_token

	def make_request(self, request_type, url, headers=None, data=None):
		if request_type == 'post':
			res = make_post_request(url, headers=headers, data=data)
		else:
			res = make_get_request(url, headers=headers, data=data)

		self.log_request(url, headers, data, res)
		return res

	def log_request(self, url, headers, data, res):
		headers.update({ 'password': self.credentials.password })
		request_log = frappe.get_doc({
			"doctype": "E Invoice Request Log",
			"user": frappe.session.user,
			"reference_invoice": self.invoice.name if self.invoice else None,
			"url": url,
			"headers": json.dumps(headers, indent=4) if headers else None,
			"data": json.dumps(data, indent=4) if isinstance(data, dict) else data,
			"response": json.dumps(res, indent=4) if res else None
		})
		request_log.save(ignore_permissions=True)
		frappe.db.commit()

	def fetch_auth_token(self):
		headers = {
			'gspappid': frappe.conf.einvoice_client_id,
			'gspappsecret': frappe.conf.einvoice_client_secret
		}
		res = {}
		try:
			res = self.make_request('post', self.authenticate_url, headers)
			self.e_invoice_settings.auth_token = "{} {}".format(res.get('token_type'), res.get('access_token'))
			self.e_invoice_settings.token_expiry = add_to_date(None, seconds=res.get('expires_in'))
			self.e_invoice_settings.save(ignore_permissions=True)
			self.e_invoice_settings.reload()

		except Exception:
			self.log_error(res)
			self.raise_error(True)

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
			res = self.make_request('get', self.gstin_details_url + params, headers)
			if res.get('success'):
				return res.get('result')
			else:
				self.log_error(res)
				raise RequestFailed

		except RequestFailed:
			self.raise_error()

		except Exception:
			self.log_error()
			self.raise_error(True)

	@staticmethod
	def get_gstin_details(gstin):
		'''fetch and cache GSTIN details'''
		if not hasattr(frappe.local, 'gstin_cache'):
			frappe.local.gstin_cache = {}

		key = gstin
		gsp_connector = GSPConnector()
		details = gsp_connector.fetch_gstin_details(gstin)

		frappe.local.gstin_cache[key] = details
		frappe.cache().hset('gstin_cache', key, details)
		return details

	def generate_irn(self):
		headers = self.get_headers()
		einvoice = make_einvoice(self.invoice)
		data = json.dumps(einvoice, indent=4)

		try:
			res = self.make_request('post', self.generate_irn_url, headers, data)
			if res.get('success'):
				self.set_einvoice_data(res.get('result'))

			elif '2150' in res.get('message'):
				# IRN already generated but not updated in invoice
				# Extract the IRN from the response description and fetch irn details
				irn = res.get('result')[0].get('Desc').get('Irn')
				irn_details = self.get_irn_details(irn)
				if irn_details:
					self.set_einvoice_data(irn_details)
				else:
					raise RequestFailed('IRN has already been generated for the invoice but cannot fetch details for the it. \
						Contact ERPNext support to resolve the issue.')

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get('message'))
			self.raise_error(errors=errors)

		except Exception:
			self.log_error(data)
			self.raise_error(True)

	def get_irn_details(self, irn):
		headers = self.get_headers()

		try:
			params = '?irn={irn}'.format(irn=irn)
			res = self.make_request('get', self.irn_details_url + params, headers)
			if res.get('success'):
				return res.get('result')
			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get('message'))
			self.raise_error(errors=errors)

		except Exception:
			self.log_error()
			self.raise_error(True)

	def cancel_irn(self, irn, reason, remark):
		headers = self.get_headers()
		data = json.dumps({
			'Irn': irn,
			'Cnlrsn': reason,
			'Cnlrem': remark
		}, indent=4)

		try:
			res = self.make_request('post', self.cancel_irn_url, headers, data)
			if res.get('success'):
				self.invoice.irn_cancelled = 1
				self.invoice.flags.updater_reference = {
					'doctype': self.invoice.doctype,
					'docname': self.invoice.name,
					'label': _('IRN Cancelled - {}').format(remark)
				}
				self.update_invoice()

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get('message'))
			self.raise_error(errors=errors)

		except Exception:
			self.log_error(data)
			self.raise_error(True)

	def generate_eway_bill(self, **kwargs):
		args = frappe._dict(kwargs)

		headers = self.get_headers()
		eway_bill_details = get_eway_bill_details(args)
		data = json.dumps({
			'Irn': args.irn,
			'Distance': cint(eway_bill_details.distance),
			'TransMode': eway_bill_details.mode_of_transport,
			'TransId': eway_bill_details.gstin,
			'TransName': eway_bill_details.transporter,
			'TrnDocDt': eway_bill_details.document_date,
			'TrnDocNo': eway_bill_details.document_name,
			'VehNo': eway_bill_details.vehicle_no,
			'VehType': eway_bill_details.vehicle_type
		}, indent=4)

		try:
			res = self.make_request('post', self.generate_ewaybill_url, headers, data)
			if res.get('success'):
				self.invoice.ewaybill = res.get('result').get('EwbNo')
				self.invoice.eway_bill_cancelled = 0
				self.invoice.update(args)
				self.invoice.flags.updater_reference = {
					'doctype': self.invoice.doctype,
					'docname': self.invoice.name,
					'label': _('E-Way Bill Generated')
				}
				self.update_invoice()

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get('message'))
			self.raise_error(errors=errors)

		except Exception:
			self.log_error(data)
			self.raise_error(True)

	def cancel_eway_bill(self, eway_bill, reason, remark):
		headers = self.get_headers()
		data = json.dumps({
			'ewbNo': eway_bill,
			'cancelRsnCode': reason,
			'cancelRmrk': remark
		}, indent=4)
		headers["username"] = headers["user_name"]
		del headers["user_name"]
		try:
			res = self.make_request('post', self.cancel_ewaybill_url, headers, data)
			if res.get('success'):
				self.invoice.ewaybill = ''
				self.invoice.eway_bill_cancelled = 1
				self.invoice.flags.updater_reference = {
					'doctype': self.invoice.doctype,
					'docname': self.invoice.name,
					'label': _('E-Way Bill Cancelled - {}').format(remark)
				}
				self.update_invoice()

			else:
				raise RequestFailed

		except RequestFailed:
			errors = self.sanitize_error_message(res.get('message'))
			self.raise_error(errors=errors)

		except Exception:
			self.log_error(data)
			self.raise_error(True)

	def sanitize_error_message(self, message):
		'''
			On validation errors, response message looks something like this:
			message = '2174 : For inter-state transaction, CGST and SGST amounts are not applicable; only IGST amount is applicable,
						3095 : Supplier GSTIN is inactive'
			we search for string between ':' to extract the error messages
			errors = [
				': For inter-state transaction, CGST and SGST amounts are not applicable; only IGST amount is applicable, 3095 ',
				': Test'
			]
			then we trim down the message by looping over errors
		'''
		errors = re.findall(': [^:]+', message)
		for idx, e in enumerate(errors):
			# remove colons
			errors[idx] = errors[idx].replace(':', '').strip()
			# if not last
			if idx != len(errors) - 1:
				# remove last 7 chars eg: ', 3095 '
				errors[idx] = errors[idx][:-6]

		return errors

	def log_error(self, data={}):
		if not isinstance(data, dict):
			data = json.loads(data)

		seperator = "--" * 50
		err_tb = traceback.format_exc()
		err_msg = str(sys.exc_info()[1])
		data = json.dumps(data, indent=4)

		message = "\n".join([
			"Error", err_msg, seperator,
			"Data:", data, seperator,
			"Exception:", err_tb
		])
		frappe.log_error(title=_('E Invoice Request Failed'), message=message)

	def raise_error(self, raise_exception=False, errors=[]):
		title = _('E Invoice Request Failed')
		if errors:
			frappe.throw(errors, title=title, as_list=1)
		else:
			link_to_error_list = '<a href="desk#List/Error Log/List?method=E Invoice Request Failed">Error Log</a>'
			frappe.msgprint(
				_('An error occurred while making e-invoicing request. Please check {} for more information.').format(link_to_error_list),
				title=title,
				raise_exception=raise_exception,
				indicator='red'
			)

	def set_einvoice_data(self, res):
		enc_signed_invoice = res.get('SignedInvoice')
		dec_signed_invoice = jwt.decode(enc_signed_invoice, verify=False)['data']

		self.invoice.irn = res.get('Irn')
		self.invoice.ewaybill = res.get('EwbNo')
		self.invoice.signed_einvoice = dec_signed_invoice
		self.invoice.signed_qr_code = res.get('SignedQRCode')

		self.attach_qrcode_image()

		self.invoice.flags.updater_reference = {
			'doctype': self.invoice.doctype,
			'docname': self.invoice.name,
			'label': _('IRN Generated')
		}
		self.update_invoice()

	def attach_qrcode_image(self):
		qrcode = self.invoice.signed_qr_code
		doctype = self.invoice.doctype
		docname = self.invoice.name
		filename = 'QRCode_{}.png'.format(docname).replace(os.path.sep, "__")

		qr_image = io.BytesIO()
		url = qrcreate(qrcode, error='L')
		url.png(qr_image, scale=2, quiet_zone=1)
		_file = frappe.get_doc({
			"doctype": "File",
			"file_name": filename,
			"attached_to_doctype": doctype,
			"attached_to_name": docname,
			"attached_to_field": "qrcode_image",
			"is_private": 1,
			"content": qr_image.getvalue()})
		_file.save()
		frappe.db.commit()
		self.invoice.qrcode_image = _file.file_url

	def update_invoice(self):
		self.invoice.flags.ignore_validate_update_after_submit = True
		self.invoice.flags.ignore_validate = True
		self.invoice.save()


def sanitize_for_json(string):
	"""Escape JSON specific characters from a string."""

	# json.dumps adds double-quotes to the string. Indexing to remove them.
	return json.dumps(string)[1:-1]

@frappe.whitelist()
def get_einvoice(doctype, docname):
	invoice = frappe.get_doc(doctype, docname)
	return make_einvoice(invoice)

@frappe.whitelist()
def generate_irn(doctype, docname):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.generate_irn()

@frappe.whitelist()
def cancel_irn(doctype, docname, irn, reason, remark):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.cancel_irn(irn, reason, remark)

@frappe.whitelist()
def generate_eway_bill(doctype, docname, **kwargs):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.generate_eway_bill(**kwargs)

@frappe.whitelist()
def cancel_eway_bill(doctype, docname, eway_bill, reason, remark):
	gsp_connector = GSPConnector(doctype, docname)
	gsp_connector.cancel_eway_bill(eway_bill, reason, remark)
