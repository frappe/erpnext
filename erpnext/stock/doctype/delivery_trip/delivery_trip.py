# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.utils import cstr, get_datetime, getdate, get_link_to_form
from frappe.utils.user import get_user_fullname


class DeliveryTrip(Document):
	def on_submit(self):
		self.update_delivery_notes()

	def on_cancel(self):
		self.update_delivery_notes(delete=True)

	def update_delivery_notes(self, delete=False):
		delivery_notes = list(set([stop.delivery_note for stop in self.delivery_stops if stop.delivery_note]))

		update_fields = {
			"transporter": self.driver,
			"transporter_name": self.driver_name,
			"transport_mode": "Road",
			"vehicle_no": self.vehicle,
			"vehicle_type": "Regular",
			"lr_no": self.name,
			"lr_date": self.date
		}

		for delivery_note in delivery_notes:
			note_doc = frappe.get_doc("Delivery Note", delivery_note)

			for field, value in update_fields.items():
				value = None if delete else value
				setattr(note_doc, field, value)

			note_doc.save()

		delivery_notes = [get_link_to_form("Delivery Note", note) for note in delivery_notes]
		frappe.msgprint(_("Delivery Notes {0} updated".format(", ".join(delivery_notes))))



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


def process_route(name, optimize):
	doc = frappe.get_doc("Delivery Trip", name)
	settings = frappe.get_single("Google Maps Settings")
	gmaps_client = settings.get_client()

	if not settings.enabled:
		frappe.throw(_("Google Maps integration is not enabled"))

	home_address = get_address_display(frappe.get_doc("Address", settings.home_address).as_dict())
	address_list = []

	for stop in doc.delivery_stops:
		address_list.append(stop.customer_address)

	# Cannot add datetime.date to datetime.timedelta
	departure_datetime = get_datetime(doc.date) + doc.departure_time

	try:
		directions = gmaps_client.directions(origin=home_address,
					destination=home_address, waypoints=address_list,
					optimize_waypoints=optimize, departure_time=departure_datetime)
	except Exception as e:
		frappe.throw((e.message))

	if not directions:
		return

	directions = directions[0]
	duration = 0

	# Google Maps returns the optimized order of the waypoints that were sent
	for idx, order in enumerate(directions.get("waypoint_order")):
		# We accordingly rearrange the rows
		doc.delivery_stops[order].idx = idx + 1
		# Google Maps returns the "legs" in the optimized order, so we loop through it
		duration += directions.get("legs")[idx].get("duration").get("value")
		arrival_datetime = departure_datetime + datetime.timedelta(seconds=duration)
		doc.delivery_stops[order].estimated_arrival = arrival_datetime

	doc.save()
	frappe.db.commit()


@frappe.whitelist()
def optimize_route(name):
	process_route(name, optimize=True)


@frappe.whitelist()
def get_arrival_times(name):
	process_route(name, optimize=False)


@frappe.whitelist()
def notify_customers(docname, date, driver, vehicle, sender_email, delivery_notification):
	sender_name = get_user_fullname(sender_email)
	attachments = []

	parent_doc = frappe.get_doc('Delivery Trip', docname)
	args = parent_doc.as_dict()

	for delivery_stop in parent_doc.delivery_stops:
		contact_info = frappe.db.get_value("Contact", delivery_stop.contact,
			["first_name", "last_name", "email_id", "gender"], as_dict=1)

		args.update(delivery_stop.as_dict())
		args.update(contact_info)

		if delivery_stop.delivery_note:
			default_print_format = frappe.get_meta('Delivery Note').default_print_format
			attachments = frappe.attach_print('Delivery Note',
				delivery_stop.delivery_note,
				file_name="Delivery Note",
				print_format=default_print_format or "Standard")

		if not delivery_stop.notified_by_email and contact_info.email_id:
			driver_info = frappe.db.get_value("Driver", driver, ["full_name", "cell_number"], as_dict=1)
			sender_designation = frappe.db.get_value("Employee", sender_email, ["designation"])

			estimated_arrival = cstr(delivery_stop.estimated_arrival)[:-3]
			email_template = frappe.get_doc("Email Template", delivery_notification)
			message = frappe.render_template(email_template.response, args)

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

def round_timedelta(td, period):
	"""Round timedelta"""
	period_seconds = period.total_seconds()
	half_period_seconds = period_seconds / 2
	remainder = td.total_seconds() % period_seconds
	if remainder >= half_period_seconds:
		return datetime.timedelta(seconds=td.total_seconds() + (period_seconds - remainder))
	else:
		return datetime.timedelta(seconds=td.total_seconds() - remainder)

def format_address(address):
	"""Customer Address format """
	address = frappe.get_doc('Address', address)
	return '{}, {}, {}, {}'.format(address.address_line1, address.city, address.pincode, address.country)
