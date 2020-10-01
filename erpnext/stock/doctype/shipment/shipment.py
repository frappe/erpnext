# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.accounts.party import get_party_shipping_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.erpnext_integrations.doctype.letmeship.letmeship import LETMESHIP_PROVIDER, get_letmeship_available_services, create_letmeship_shipment, get_letmeship_label, get_letmeship_tracking_data
from erpnext.erpnext_integrations.doctype.packlink.packlink import PACKLINK_PROVIDER, get_packlink_available_services, create_packlink_shipment, get_packlink_label, get_packlink_tracking_data
from erpnext.erpnext_integrations.doctype.sendcloud.sendcloud import SENDCLOUD_PROVIDER, get_sendcloud_available_services, create_sendcloud_shipment, get_sendcloud_label, get_sendcloud_tracking_data
from erpnext.stock.doctype.parcel_service_type.parcel_service_type import match_parcel_service_type_alias

class Shipment(Document):
	def validate(self):
		self.validate_weight()
		if self.docstatus == 0:
			self.status = 'Draft'

	def on_submit(self):
		if not self.shipment_parcel:
			frappe.throw(_('Please enter Shipment Parcel information'))
		if self.value_of_goods == 0:
			frappe.throw(_('Value of goods cannot be 0'))
		self.status = 'Submitted'

	def on_cancel(self):
		self.status = 'Cancelled'

	def validate_weight(self):
		for parcel in self.shipment_parcel:
			if flt(parcel.weight) <= 0:
				frappe.throw(_('Parcel weight cannot be 0'))

@frappe.whitelist()
def fetch_shipping_rates(pickup_from_type, delivery_to_type, pickup_address_name, delivery_address_name,
		shipment_parcel, description_of_content, pickup_date, value_of_goods,
		pickup_contact_name=None, delivery_contact_name=None):
	# Return Shipping Rates for the various Shipping Providers
	shipment_prices = []
	letmeship_enabled = frappe.db.get_single_value('LetMeShip','enabled')
	packlink_enabled = frappe.db.get_single_value('Packlink','enabled')
	sendcloud_enabled = frappe.db.get_single_value('SendCloud','enabled')
	pickup_address = get_address(pickup_address_name)
	delivery_address = get_address(delivery_address_name)
	if letmeship_enabled:
		pickup_contact = None
		delivery_contact = None
		if pickup_from_type != 'Company':
			pickup_contact = get_contact(pickup_contact_name)
		else:
			pickup_contact = get_company_contact(user=pickup_contact_name)
		
		if delivery_to_type != 'Company':
			delivery_contact = get_contact(delivery_contact_name)
		else:
			delivery_contact = get_company_contact(user=pickup_contact_name)
		letmeship_prices = get_letmeship_available_services(
			delivery_to_type=delivery_to_type,
			pickup_address=pickup_address,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel,
			description_of_content=description_of_content,
			pickup_date=pickup_date,
			value_of_goods=value_of_goods,
			pickup_contact=pickup_contact,
			delivery_contact=delivery_contact,
		)
		letmeship_prices = match_parcel_service_type_carrier(letmeship_prices, ['carrier', 'carrier_name'])
		shipment_prices = shipment_prices + letmeship_prices
	if packlink_enabled:
		packlink_prices = get_packlink_available_services(
			pickup_address=pickup_address,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel, 
			pickup_date=pickup_date
		)
		packlink_prices = match_parcel_service_type_carrier(packlink_prices, ['carrier_name', 'carrier'])
		shipment_prices = shipment_prices + packlink_prices
	if sendcloud_enabled and pickup_from_type == 'Company':
		sendcloud_prices = get_sendcloud_available_services(
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel
		)
		shipment_prices = shipment_prices + sendcloud_prices
	shipment_prices = sorted(shipment_prices, key=lambda k:k['total_price'])
	return shipment_prices

@frappe.whitelist()
def create_shipment(shipment, pickup_from_type, delivery_to_type, pickup_address_name,
		delivery_address_name, shipment_parcel, description_of_content, pickup_date,
		value_of_goods, service_data, shipment_notific_email, tracking_notific_email,
		pickup_contact_name=None, delivery_contact_name=None, delivery_notes=[]):
	# Create Shipment for the selected provider
	service_info = json.loads(service_data)
	shipment_info = None
	pickup_contact = None
	delivery_contact = None
	pickup_address = get_address(pickup_address_name)
	delivery_address = get_address(delivery_address_name)
	if pickup_from_type != 'Company':
		pickup_contact = get_contact(pickup_contact_name)
	else:
		pickup_contact = get_company_contact(user=pickup_contact_name)
	
	if delivery_to_type != 'Company':
		delivery_contact = get_contact(delivery_contact_name)
	else:
		delivery_contact = get_company_contact(user=pickup_contact_name)
	if service_info['service_provider'] == LETMESHIP_PROVIDER:
		shipment_info = create_letmeship_shipment(
			pickup_address=pickup_address,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel,
			description_of_content=description_of_content,
			pickup_date=pickup_date,
			value_of_goods=value_of_goods,
			pickup_contact=pickup_contact,
			delivery_contact=delivery_contact,
			service_info=service_info,
			shipment_notific_email=shipment_notific_email,
			tracking_notific_email=tracking_notific_email,
		)

	if service_info['service_provider'] == PACKLINK_PROVIDER:
		shipment_info = create_packlink_shipment(
			pickup_address=pickup_address,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel,
			description_of_content=description_of_content,
			pickup_date=pickup_date,
			value_of_goods=value_of_goods,
			pickup_contact=pickup_contact,
			delivery_contact=delivery_contact,
			service_info=service_info,
		)

	if service_info['service_provider'] == SENDCLOUD_PROVIDER:
		shipment_info = create_sendcloud_shipment(
			shipment=shipment,
			delivery_address=delivery_address,
			shipment_parcel=shipment_parcel,
			description_of_content=description_of_content,
			value_of_goods=value_of_goods,
			delivery_contact=delivery_contact,
			service_info=service_info,
		)

	if shipment_info:
		fields = ['service_provider', 'carrier', 'carrier_service', 'shipment_id', 'shipment_amount', 'awb_number']
		for field in fields:
			frappe.db.set_value('Shipment', shipment, field, shipment_info.get(field))
		frappe.db.set_value('Shipment', shipment, 'status', 'Booked')
		if delivery_notes:
			update_delivery_note(delivery_notes=delivery_notes, shipment_info=shipment_info)
	return shipment_info


@frappe.whitelist()
def print_shipping_label(service_provider, shipment_id):
	if service_provider == LETMESHIP_PROVIDER:
		shipping_label = get_letmeship_label(shipment_id)
	elif service_provider == PACKLINK_PROVIDER:
		shipping_label = get_packlink_label(shipment_id)
	elif service_provider == SENDCLOUD_PROVIDER:
		shipping_label = get_sendcloud_label(shipment_id)
	return shipping_label


@frappe.whitelist()
def update_tracking(shipment, service_provider, shipment_id, delivery_notes=[]):
	# Update Tracking info in Shipment
	tracking_data = None
	if service_provider == LETMESHIP_PROVIDER:
		tracking_data = get_letmeship_tracking_data(shipment_id)
	elif service_provider == PACKLINK_PROVIDER:
		tracking_data = get_packlink_tracking_data(shipment_id)
	elif service_provider == SENDCLOUD_PROVIDER:
		tracking_data = get_sendcloud_tracking_data(shipment_id)
	if tracking_data:
		if delivery_notes:
			update_delivery_note(delivery_notes=delivery_notes, tracking_info=tracking_data)
		frappe.db.set_value('Shipment', shipment, 'awb_number', tracking_data.get('awb_number'))
		frappe.db.set_value('Shipment', shipment, 'tracking_status', tracking_data.get('tracking_status'))
		frappe.db.set_value('Shipment', shipment, 'tracking_status_info', tracking_data.get('tracking_status_info'))
		frappe.db.set_value('Shipment', shipment, 'tracking_url', tracking_data.get('tracking_url'))

@frappe.whitelist()
def get_address_name(ref_doctype, docname):
	# Return address name
	return get_party_shipping_address(ref_doctype, docname)

@frappe.whitelist()
def get_contact_name(ref_doctype, docname):
	# Return address name
	return get_default_contact(ref_doctype, docname)

def update_delivery_note(delivery_notes, shipment_info=None, tracking_info=None):
	# Update Shipment Info in Delivery Note
	# Using db_set since some services might not exist
	for delivery_note in json.loads(delivery_notes):
		dl_doc = frappe.get_doc('Delivery Note', delivery_note)
		if shipment_info:
			dl_doc.db_set('delivery_type', 'Parcel Service')
			dl_doc.db_set('parcel_service', shipment_info.get('carrier'))
			dl_doc.db_set('parcel_service_type', shipment_info.get('carrier_service'))
		if tracking_info:		
			dl_doc.db_set('tracking_number', tracking_info.get('awb_number'))
			dl_doc.db_set('tracking_url', tracking_info.get('tracking_url'))
			dl_doc.db_set('tracking_status', tracking_info.get('tracking_status'))
			dl_doc.db_set('tracking_status_info', tracking_info.get('tracking_status_info'))


def update_tracking_info():
	# Daily scheduled event to update Tracking info for not delivered Shipments
	# Also Updates the related Delivery Notes
	shipments = frappe.get_all('Shipment', filters={
		'docstatus': 1,
		'status': 'Booked',
		'shipment_id': ['!=', ''],
		'tracking_status': ['!=', 'Delivered'],
	})
	for shipment in shipments:
		shipment_doc = frappe.get_doc('Shipment', shipment.name)
		tracking_info = \
			update_tracking(
				shipment_doc.service_provider,
				shipment_doc.shipment_id,
				shipment_doc.shipment_delivery_notes
			)
		if tracking_info:
			shipment_doc.db_set('awb_number', tracking_info.get('awb_number'))
			shipment_doc.db_set('tracking_url', tracking_info.get('tracking_url'))
			shipment_doc.db_set('tracking_status', tracking_info.get('tracking_status'))
			shipment_doc.db_set('tracking_status_info', tracking_info.get('tracking_status_info'))


def get_address(address_name):
	address = frappe.db.get_value('Address', address_name, [
		'address_title',
		'address_line1',
		'address_line2',
		'city',
		'pincode',
		'country',
	], as_dict=1)
	address.country_code = frappe.db.get_value('Country', address.country, 'code').upper()
	if not address.pincode or address.pincode == '':
		frappe.throw(_("Postal Code is mandatory to continue. </br> \
				Please set Postal Code for Address <a href='#Form/Address/{0}'>{1}</a>"
			).format(address_name, address_name))
	address.pincode = address.pincode.replace(' ', '')
	address.city = address.city.strip()
	return address


def get_contact(contact_name):
	contact = frappe.db.get_value('Contact', contact_name, [
		'first_name',
		'last_name',
		'email_id',
		'phone',
		'mobile_no',
		'gender',
	], as_dict=1)
	if not contact.last_name:
		frappe.throw(_("Last Name is mandatory to continue. </br> \
				Please set Last Name for Contact <a href='#Form/Contact/{0}'>{1}</a>"
			).format(contact_name, contact_name))
	if not contact.phone:
		contact.phone = contact.mobile_no
	return contact

def match_parcel_service_type_carrier(shipment_prices, reference):
	for idx, prices in enumerate(shipment_prices):
		service_name = match_parcel_service_type_alias(prices.get(reference[0]), prices.get(reference[1]))
		is_preferred = frappe.db.get_value('Parcel Service Type', service_name, 'show_in_preferred_services_list')
		shipment_prices[idx].service_name = service_name
		shipment_prices[idx].is_preferred = is_preferred
	return shipment_prices

@frappe.whitelist()
def get_company_contact(user):
	contact = frappe.db.get_value('User', user, [
		'first_name',
		'last_name',
		'email',
		'phone',
		'mobile_no',
		'gender',
	], as_dict=1)
	if not contact.phone:
		contact.phone = contact.mobile_no
	return contact