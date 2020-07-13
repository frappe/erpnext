# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import requests
import frappe
import json
import re
from frappe import _
from frappe.model.document import Document
from erpnext.erpnext_integrations.utils import get_tracking_url

LETMESHIP_PROVIDER = 'LetMeShip'

class LetMeShip(Document):
	pass

def get_letmeship_available_services(delivery_to_type, pickup_address,
	delivery_address, shipment_parcel, description_of_content, pickup_date,
	value_of_goods, pickup_contact=None, delivery_contact=None):
	# Retrieve rates at LetMeShip from specification stated.
	enabled = frappe.db.get_single_value('LetMeShip','enabled')
	api_id = frappe.db.get_single_value('LetMeShip','api_id')
	api_password = frappe.db.get_single_value('LetMeShip','api_password')
	if not enabled or not api_id or not api_password:
		return []

	set_letmeship_specific_fields(pickup_contact, delivery_contact)

	# LetMeShip have limit of 30 characters for Company field
	if len(pickup_address.address_title) > 30:
		pickup_address.address_title = pickup_address.address_title[:30]
	if len(delivery_address.address_title) > 30:
		delivery_address.address_title = delivery_address.address_title[:30]
	parcel_list = get_parcel_list(json.loads(shipment_parcel), description_of_content)

	url = 'https://api.letmeship.com/v1/available'
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'Access-Control-Allow-Origin': 'string'
	}
	payload = {'pickupInfo': {
		'address': {
			'countryCode': pickup_address.country_code,
			'zip': pickup_address.pincode,
			'city': pickup_address.city,
			'street': pickup_address.address_line1,
			'addressInfo1': pickup_address.address_line2,
			'houseNo': '',
		},
		'company': pickup_address.address_title,
		'person': {
			'title': pickup_contact.title,
			'firstname': pickup_contact.first_name,
			'lastname': pickup_contact.last_name
		},
		'phone': {
			'phoneNumber': pickup_contact.phone,
			'phoneNumberPrefix': pickup_contact.phone_prefix
		},
		'email': pickup_contact.email,
	}, 'deliveryInfo': {
		'address': {
			'countryCode': delivery_address.country_code,
			'zip': delivery_address.pincode,
			'city': delivery_address.city,
			'street': delivery_address.address_line1,
			'addressInfo1': delivery_address.address_line2,
			'houseNo': '',
		},
		'company': delivery_address.address_title,
		'person': {
			'title': delivery_contact.title,
			'firstname': delivery_contact.first_name,
			'lastname': delivery_contact.last_name
		},
		'phone': {
			'phoneNumber': delivery_contact.phone,
			'phoneNumberPrefix': delivery_contact.phone_prefix
		},
		'email': delivery_contact.email,
	}, 'shipmentDetails': {
		'contentDescription': description_of_content,
		'shipmentType': 'PARCEL',
		'shipmentSettings': {
			'saturdayDelivery': False,
			'ddp': False,
			'insurance': False,
			'pickupOrder': False,
			'pickupTailLift': False,
			'deliveryTailLift': False,
			'holidayDelivery': False,
		},
		'goodsValue': value_of_goods,
		'parcelList': parcel_list,
		'pickupInterval': {'date': pickup_date},
	}}
	try:
		available_services = []
		response_data = requests.post(
			url=url,
			auth=(api_id, api_password), 
			headers=headers,
			data=json.dumps(payload)
		)
		response_data = json.loads(response_data.text)
		if 'serviceList' in response_data:
			for response in response_data['serviceList']:
				available_service = frappe._dict()
				basic_info = response['baseServiceDetails']
				price_info = basic_info['priceInfo']
				available_service.service_provider = LETMESHIP_PROVIDER
				available_service.id = basic_info['id']
				available_service.carrier = basic_info['carrier']
				available_service.carrier_name = basic_info['name']
				available_service.service_name = ''
				available_service.is_preferred = 0
				available_service.real_weight = price_info['realWeight']
				available_service.total_price = price_info['netPrice']
				available_service.price_info = price_info
				available_services.append(available_service)
			return available_services
		else:
			frappe.throw(
				_('Error occurred while fetching LetMeShip prices: {0}')
					.format(response_data['message'])
			)
	except Exception as exc:
		frappe.msgprint(
			_('Error occurred while fetching LetMeShip Prices: {0}')
				.format(str(exc)),
			indicator='orange',
			alert=True
		)
	return []


def create_letmeship_shipment(pickup_address, delivery_address, shipment_parcel, description_of_content,
	pickup_date, value_of_goods, service_info, shipment_notific_email, tracking_notific_email,
	pickup_contact=None, delivery_contact=None):
	# Create a transaction at LetMeShip
	# LetMeShip have limit of 30 characters for Company field
	enabled = frappe.db.get_single_value('LetMeShip','enabled')
	api_id = frappe.db.get_single_value('LetMeShip','api_id')
	api_password = frappe.db.get_single_value('LetMeShip','api_password')
	if not enabled or not api_id or not api_password:
		return []

	set_letmeship_specific_fields(pickup_contact, delivery_contact)

	if len(pickup_address.address_title) > 30:
		pickup_address.address_title = pickup_address.address_title[:30]
	if len(delivery_address.address_title) > 30:
		delivery_address.address_title = delivery_address.address_title[:30]

	parcel_list = get_parcel_list(json.loads(shipment_parcel), description_of_content)
	url = 'https://api.letmeship.com/v1/shipments'
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'Access-Control-Allow-Origin': 'string'
	}
	payload = {
		'pickupInfo': {
			'address': {
				'countryCode': pickup_address.country_code,
				'zip': pickup_address.pincode,
				'city': pickup_address.city,
				'street': pickup_address.address_line1,
				'addressInfo1': pickup_address.address_line2,
				'houseNo': '',
			},
			'company': pickup_address.address_title,
			'person': {
				'title': pickup_contact.title,
				'firstname': pickup_contact.first_name,
				'lastname': pickup_contact.last_name
			},
			'phone': {
				'phoneNumber': pickup_contact.phone,
				'phoneNumberPrefix': pickup_contact.phone_prefix
			},
			'email': pickup_contact.email,
		},
		'deliveryInfo': {
			'address': {
				'countryCode': delivery_address.country_code,
				'zip': delivery_address.pincode,
				'city': delivery_address.city,
				'street': delivery_address.address_line1,
				'addressInfo1': delivery_address.address_line2,
				'houseNo': '',
			},
			'company': delivery_address.address_title,
			'person': {
				'title': delivery_contact.title,
				'firstname': delivery_contact.first_name,
				'lastname': delivery_contact.last_name
			},
			'phone': {
				'phoneNumber': delivery_contact.phone,
				'phoneNumberPrefix': delivery_contact.phone_prefix
			},
			'email': delivery_contact.email,
		},
		'service': {
			'baseServiceDetails': {
				'id': service_info['id'],
				'name': service_info['service_name'],
				'carrier': service_info['carrier'],
				'priceInfo': service_info['price_info'],
			},
			'supportedExWorkType': [],
			'messages': [''],
			'description': '',
			'serviceInfo': '',
		},
		'shipmentDetails': {
			'contentDescription': description_of_content,
			'shipmentType': 'PARCEL',
			'shipmentSettings': {
				'saturdayDelivery': False,
				'ddp': False,
				'insurance': False,
				'pickupOrder': False,
				'pickupTailLift': False,
				'deliveryTailLift': False,
				'holidayDelivery': False,
			},
			'goodsValue': value_of_goods,
			'parcelList': parcel_list,
			'pickupInterval': {
				'date': pickup_date
			},
			'contentDescription': description_of_content,
		},
		'shipmentNotification': {
			'trackingNotification': {
				'deliveryNotification': True,
				'problemNotification': True,
				'emails': [tracking_notific_email],
				'notificationText': '',
			}, 
			'recipientNotification': {
				'notificationText': '',
				'emails': [ shipment_notific_email ]
			}
		},
		'labelEmail': True,
	}
	try:
		response_data = requests.post(
			url=url,
			auth=(api_id, api_password),
			headers=headers,
			data=json.dumps(payload)
		)
		response_data = json.loads(response_data.text)
		if 'shipmentId' in response_data:
			shipment_amount = response_data['service']['priceInfo']['totalPrice']
			awb_number = ''
			url = 'https://api.letmeship.com/v1/shipments/{id}'.format(id=response_data['shipmentId'])
			tracking_response = requests.get(url, auth=(api_id, api_password),headers=headers)
			tracking_response_data = json.loads(tracking_response.text)
			if 'trackingData' in tracking_response_data:
				for parcel in tracking_response_data['trackingData']['parcelList']:
					if 'awbNumber' in parcel:
						awb_number = parcel['awbNumber']
			return {
				'service_provider': LETMESHIP_PROVIDER,
				'shipment_id': response_data['shipmentId'],
				'carrier': service_info['carrier'],
				'carrier_service': service_info['service_name'],
				'shipment_amount': shipment_amount,
				'awb_number': awb_number,
			}
		elif 'message' in response_data:
			frappe.throw(
				_('Error occurred while creating Shipment: {0}')
					.format(response_data['message'])
			)
	except Exception as exc:
		frappe.msgprint(
			_('Error occurred while creating Shipment: {0}')
				.format(str(exc)),
			indicator='orange',
			alert=True
		)


def get_letmeship_label(shipment_id):
	# Retrieve shipment label from LetMeShip
	api_id = frappe.db.get_single_value('LetMeShip','api_id')
	api_password = frappe.db.get_single_value('LetMeShip','api_password')
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'Access-Control-Allow-Origin': 'string'
	}
	url = 'https://api.letmeship.com/v1/shipments/{id}/documents?types=LABEL'\
		.format(id=shipment_id)
	shipment_label_response = requests.get(
		url,
		auth=(api_id,api_password),
		headers=headers
	)
	shipment_label_response_data = json.loads(shipment_label_response.text)
	if 'documents' in shipment_label_response_data:
		for label in shipment_label_response_data['documents']:
			if 'data' in label:
				return json.dumps(label['data'])
	else:
		frappe.throw(
			_('Error occurred while printing Shipment: {0}')
				.format(shipment_label_response_data['message'])
		)


def get_letmeship_tracking_data(shipment_id):
	# return letmeship tracking data
	api_id = frappe.db.get_single_value('LetMeShip','api_id')
	api_password = frappe.db.get_single_value('LetMeShip','api_password')
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'Access-Control-Allow-Origin': 'string'
	}
	try:
		url = 'https://api.letmeship.com/v1/tracking?shipmentid={id}'.format(id=shipment_id)
		tracking_data_response = requests.get(
			url,
			auth=(api_id, api_password),
			headers=headers
		)
		tracking_data = json.loads(tracking_data_response.text)
		if 'awbNumber' in tracking_data:
			tracking_status = 'In Progress'
			if tracking_data['lmsTrackingStatus'].startswith('DELIVERED'):
				tracking_status = 'Delivered'
			if tracking_data['lmsTrackingStatus'] == 'RETURNED':
				tracking_status = 'Returned'
			if tracking_data['lmsTrackingStatus'] == 'LOST':
				tracking_status = 'Lost'
			tracking_url = get_tracking_url(
				carrier=tracking_data['carrier'],
				tracking_number=tracking_data['awbNumber']
			)
			return {
				'awb_number': tracking_data['awbNumber'],
				'tracking_status': tracking_status,
				'tracking_status_info': tracking_data['lmsTrackingStatus'],
				'tracking_url': tracking_url,
			}
		elif 'message' in tracking_data:
			frappe.throw(
				_('Error occurred while updating Shipment: {0}')
					.format(tracking_data['message'])
			)
	except Exception as exc:
		frappe.msgprint(
			_('Error occurred while updating Shipment: {0}')
				.format(str(exc)),
			indicator='orange',
			alert=True
		)


def get_parcel_list(shipment_parcel, description_of_content):
	parcel_list = []
	for parcel in shipment_parcel:
		formatted_parcel = {}
		formatted_parcel['height'] = parcel.get('height')
		formatted_parcel['width'] = parcel.get('width')
		formatted_parcel['length'] = parcel.get('length')
		formatted_parcel['weight'] = parcel.get('weight')
		formatted_parcel['quantity'] = parcel.get('count')
		formatted_parcel['contentDescription'] = description_of_content
		parcel_list.append(formatted_parcel)
	return parcel_list

def set_letmeship_specific_fields(pickup_contact, delivery_contact):
	pickup_contact.phone_prefix = pickup_contact.phone[:3]
	pickup_contact.phone = re.sub('[^A-Za-z0-9]+', '', pickup_contact.phone[3:])

	pickup_contact.title = 'MS'
	if pickup_contact.gender == 'Male':
		pickup_contact.title = 'MR'

	delivery_contact.phone_prefix = delivery_contact.phone[:3]
	delivery_contact.phone = re.sub('[^A-Za-z0-9]+', '', delivery_contact.phone[3:])

	delivery_contact.title = 'MS'
	if delivery_contact.gender == 'Male':
		delivery_contact.title = 'MR'