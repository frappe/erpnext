# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import requests
import frappe
import json
from frappe import _
from frappe.model.document import Document

SENDCLOUD_PROVIDER = 'SendCloud'

class SendCloud(Document):
	pass

def get_sendcloud_available_services(delivery_address, shipment_parcel):
	# Retrieve rates at SendCloud from specification stated.
	enabled = frappe.db.get_single_value('SendCloud', 'enabled')
	api_key = frappe.db.get_single_value('SendCloud', 'api_key')
	api_secret = frappe.db.get_single_value('SendCloud', 'api_secret')
	if not enabled or not api_key or not api_secret:
		return []

	try:
		url = 'https://panel.sendcloud.sc/api/v2/shipping_methods'
		responses = requests.get(url, auth=(api_key, api_secret))
		responses_dict = json.loads(responses.text)

		available_services = []
		for service in responses_dict['shipping_methods']:
			for country in service['countries']:
				if country['iso_2'] == delivery_address.country_code:
					available_service = frappe._dict()
					available_service.service_provider = 'SendCloud'
					available_service.carrier = service['carrier']
					available_service.service_name = service['name']
					available_service.total_price = total_parcel_price(country['price'], json.loads(shipment_parcel))
					available_service.service_id = service['id']
					available_services.append(available_service)
		return available_services
	except Exception as exc:
		frappe.msgprint(_('Error occurred on SendCloud: {0}').format(
			str(exc)), indicator='orange', alert=True)

def create_sendcloud_shipment(
	shipment,
	delivery_address,
	delivery_contact,
	service_info,
	shipment_parcel,
	description_of_content,
	value_of_goods
):
	# Create a transaction at SendCloud
	enabled = frappe.db.get_single_value('SendCloud', 'enabled')
	api_key = frappe.db.get_single_value('SendCloud', 'api_key')
	api_secret = frappe.db.get_single_value('SendCloud', 'api_secret')
	if not enabled or not api_key or not api_secret:
		return []

	parcels = []
	for i, parcel in enumerate(json.loads(shipment_parcel), start=1):
		parcel_data = {
			'name': "{} {}".format(delivery_contact.first_name, delivery_contact.last_name),
			'company_name': delivery_address.address_title,
			'address': delivery_address.address_line1,
			'address_2': delivery_address.address_line2 or '',
			'city': delivery_address.city,
			'postal_code': delivery_address.pincode,
			'telephone': delivery_contact.phone,
			'request_label': True,
			'email': delivery_contact.email,
			'data': [],
			'country': delivery_address.country_code,
			'shipment': {
				'id': service_info['service_id']
			},
			'order_number': "{}-{}".format(shipment, i),
			'external_reference': "{}-{}".format(shipment, i),
			'weight': parcel.get('weight'),
			'parcel_items': get_parcel_items(parcel, description_of_content, value_of_goods)
		}
		parcels.append(parcel_data)
	data = {
		'parcels': parcels
	}
	try:
		url = 'https://panel.sendcloud.sc/api/v2/parcels?errors=verbose'
		response_data = requests.post(url, json=data, auth=(api_key, api_secret))
		response_data = json.loads(response_data.text)
		if 'failed_parcels' in response_data:
			frappe.msgprint(_('Error occurred while creating Shipment: {0}'
									).format(response_data['failed_parcels'][0]['errors']), indicator='orange',
								alert=True)
		else:
			shipment_id = ', '.join([str(x['id']) for x in response_data['parcels']])
			awb_number = ', '.join([str(x['tracking_number']) for x in response_data['parcels']])
			return {
				'service_provider': 'SendCloud',
				'shipment_id': shipment_id,
				'carrier': service_info['carrier'],
				'carrier_service': service_info['service_name'],
				'shipment_amount': service_info['total_price'],
				'awb_number': awb_number
			}
	except Exception as exc:
		frappe.msgprint(_('Error occurred while creating Shipment: {0}').format(
			str(exc)), indicator='orange', alert=True)

def get_sendcloud_label(shipment_id):
	# Retrieve shipment label from SendCloud
	api_key = frappe.db.get_single_value('SendCloud', 'api_key')
	api_secret = frappe.db.get_single_value('SendCloud', 'api_secret')
	shipment_id_list = shipment_id.split(', ')
	label_urls = []
	for ship_id in shipment_id_list:
		shipment_label_response = \
			requests.get('https://panel.sendcloud.sc/api/v2/labels/{id}'.format(id=ship_id), auth=(api_key, api_secret))
		shipment_label = json.loads(shipment_label_response.text)
		label_urls.append(shipment_label['label']['label_printer'])
	if len(label_urls):
		return label_urls
	else:
		frappe.msgprint(_('Shipment ID not found'))

def get_sendcloud_tracking_data(shipment_id):
	# return SendCloud tracking data 
	try:
		api_key = frappe.db.get_single_value('SendCloud', 'api_key')
		api_secret = frappe.db.get_single_value('SendCloud', 'api_secret')
		shipment_id_list = shipment_id.split(', ')
		tracking_url = ''
		awb_number = []
		tracking_status = []
		tracking_status_info = []
		for ship_id in shipment_id_list:
			tracking_data_response = \
				requests.get('https://panel.sendcloud.sc/api/v2/parcels/{id}'.format(id=ship_id), auth=(api_key, api_secret))
			tracking_data = json.loads(tracking_data_response.text)
			tracking_url_template = \
				'<a href="{{ tracking_url }}" target="_blank"><b>{{ _("Click here to Track Shipment") }}</b></a><br>'
			tracking_url += frappe.render_template(tracking_url_template, {'tracking_url': tracking_data['parcel']['tracking_url']})
			awb_number.append(tracking_data['parcel']['tracking_number'])
			tracking_status.append(tracking_data['parcel']['status']['message'])
			tracking_status_info.append(tracking_data['parcel']['status']['message'])
		return {
			'awb_number': ', '.join(awb_number),
			'tracking_status': ', '.join(tracking_status),
			'tracking_status_info': ', '.join(tracking_status_info),
			'tracking_url': tracking_url
		}
	except Exception as exc:
		frappe.msgprint(_('Error occurred while updating Shipment: {0}').format(
			str(exc)), indicator='orange', alert=True)

def total_parcel_price(parcel_price, shipment_parcel):
	count = 0
	for parcel in shipment_parcel:
		count += parcel.get('count')
	return parcel_price * count

def get_parcel_items(parcel, description_of_content, value_of_goods):
	parcel_list = []
	formatted_parcel = {}
	formatted_parcel['description'] = description_of_content
	formatted_parcel['quantity'] = parcel.get('count')
	formatted_parcel['weight'] = parcel.get('weight')
	formatted_parcel['value'] = value_of_goods
	parcel_list.append(formatted_parcel)
	return parcel_list