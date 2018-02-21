# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime
import frappe
import googlemaps
from frappe import _
from frappe.model.document import Document
from frappe.utils.user import get_user_fullname
from frappe.utils import getdate
from frappe.integrations.doctype.google_maps.google_maps import round_timedelta
from frappe.integrations.doctype.google_maps.google_maps import format_address

class DeliveryTrip(Document):
	pass

def get_default_contact(out, name):
	contact_persons = frappe.db.sql(
		"""
			select parent,
				(select is_primary_contact from tabContact c where c.name = dl.parent)
			 	as is_primary_contact
			from
				`tabDynamic Link` dl
			where
				dl.link_doctype="Customer" and
				dl.link_name=%s and
				dl.parenttype = 'Contact'
		""", (name), as_dict=1)

	if contact_persons:
		for out.contact_person in contact_persons:
			if out.contact_person.is_primary_contact:
				return out.contact_person
		out.contact_person = contact_persons[0]
		return out.contact_person
	else:
		return None

def get_default_address(out, name):
	shipping_addresses = frappe.db.sql(
		"""
			select parent,
				(select is_shipping_address from tabAddress a where a.name=dl.parent) as is_shipping_address
			from `tabDynamic Link` dl
			where link_doctype="Customer"
				and link_name=%s
				and parenttype = 'Address'
		""", (name), as_dict=1)

	if shipping_addresses:
		for out.shipping_address in shipping_addresses:
			if out.shipping_address.is_shipping_address:
				return out.shipping_address
		out.shipping_address = shipping_addresses[0]
		return out.shipping_address
	else:
		return None


@frappe.whitelist()
def get_contact_and_address(name):
	out = frappe._dict()
	get_default_contact(out, name)
	get_default_address(out, name)
	return out


@frappe.whitelist()
def get_contact_display(contact):
	contact_info = frappe.db.get_value(
		"Contact", contact,
		["first_name", "last_name", "phone", "mobile_no"],
	as_dict=1)
	contact_info.html = """ <b>%(first_name)s %(last_name)s</b> <br> %(phone)s <br> %(mobile_no)s""" % {
		"first_name": contact_info.first_name,
		"last_name": contact_info.last_name or "",
		"phone": contact_info.phone or "",
		"mobile_no": contact_info.mobile_no or "",
	}
	return contact_info.html


@frappe.whitelist()
def get_delivery_notes(customer):
	return frappe.db.get_all("Delivery Note", filters={
		'customer': customer,
		'docstatus': 1
	})

@frappe.whitelist()
def calculate_time_matrix(name):
	"""Calucation and round in closest 15 minutes, delivery stops"""

	gmaps = frappe.db.get_value('Google Maps', None,
		['client_key', 'enabled', 'home_address'], as_dict=1)

	if not gmaps.enabled:
		frappe.throw(_("Google Maps integration is not enabled"))

	try:
		gmaps_client = googlemaps.Client(key=gmaps.client_key)
	except Exception as e:
		frappe.throw(e.message)

	secs_15min = 900
	doc = frappe.get_doc('Delivery Trip', name)
	departure_time = doc.departure_time
	matrix_duration = []

	for i, stop in enumerate(doc.delivery_stops):
		if i == 0:
			# The first row is the starting pointing
			origin = gmaps.home_address
			destination = format_address(doc.delivery_stops[i].address)
			distance_calc = gmaps_client.distance_matrix(origin, destination)
			matrix_duration.append(distance_calc)

			try:
				distance_secs = distance_calc['rows'][0]['elements'][0]['duration']['value']
			except Exception as e:
				frappe.throw(_("Error '{0}' occured. Arguments {1}.").format(e.message, e.args))

			stop.estimated_arrival = round_timedelta(
				departure_time + datetime.timedelta(0, distance_secs + secs_15min),
				datetime.timedelta(minutes=15))
		else:
			# Calculation based on previous
			origin = format_address(doc.delivery_stops[i - 1].address)
			destination = format_address(doc.delivery_stops[i].address)
			distance_calc = gmaps_client.distance_matrix(origin, destination)
			matrix_duration.append(distance_calc)

			try:
				distance_secs = distance_calc['rows'][0]['elements'][0]['duration']['value']
			except Exception as e:
				frappe.throw(_("Error '{0}' occured. Arguments {1}.").format(e.message, e.args))

			stop.estimated_arrival = round_timedelta(
				doc.delivery_stops[i - 1].estimated_arrival +
				datetime.timedelta(0, distance_secs + secs_15min), datetime.timedelta(minutes=15))
		stop.save()
		frappe.db.commit()

	return matrix_duration

@frappe.whitelist()
def notify_customers(docname, date, driver, vehicle, sender_email, delivery_notification):
	sender_name = get_user_fullname(sender_email)
	delivery_stops = frappe.get_all('Delivery Stop', {"parent": docname})
	attachments = []

	for delivery_stop in delivery_stops:
		delivery_stop_info = frappe.db.get_value(
			"Delivery Stop",
			delivery_stop.name,
			["notified_by_email", "estimated_arrival", "details", "contact", "delivery_notes"],
		as_dict=1)
		contact_info = frappe.db.get_value("Contact", delivery_stop_info.contact,
			["first_name", "last_name", "email_id", "gender"], as_dict=1)

		if delivery_stop_info.delivery_notes:
			delivery_notes = (delivery_stop_info.delivery_notes).split(",")
			default_print_format = frappe.get_meta('Delivery Note').default_print_format
			attachments = []
			for delivery_note in delivery_notes:
				attachments.append(
					frappe.attach_print('Delivery Note',
	 					 delivery_note,
						 file_name="Delivery Note",
						 print_format=default_print_format or "Standard"))

		if not delivery_stop_info.notified_by_email and contact_info.email_id:
			driver_info = frappe.db.get_value("Driver", driver, ["full_name", "cell_number"], as_dict=1)
			sender_designation = frappe.db.get_value("Employee", sender_email, ["designation"])

			estimated_arrival = str(delivery_stop_info.estimated_arrival)[:-3]
			email_template = frappe.get_doc("Standard Reply", delivery_notification)
			message = frappe.render_template(
				email_template.response,
				dict(contact_info=contact_info, sender_name=sender_name,
					details=delivery_stop_info.details,
					estimated_arrival=estimated_arrival,
					date=getdate(date).strftime('%d.%m.%y'), vehicle=vehicle,
					driver_info=driver_info,
					sender_designation=sender_designation)
			)
			frappe.sendmail(
				recipients=contact_info.email_id,
				sender=sender_email,
				message=message,
				attachments=attachments,
				subject=_(email_template.subject).format(getdate(date).strftime('%d.%m.%y'),
					estimated_arrival))

			frappe.db.set_value("Delivery Stop", delivery_stop.name, "notified_by_email", 1)
			frappe.db.set_value("Delivery Stop", delivery_stop.name,
				"email_sent_to", contact_info.email_id)
			frappe.msgprint(_("Email sent to {0}").format(contact_info.email_id))