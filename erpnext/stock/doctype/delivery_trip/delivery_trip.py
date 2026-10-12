# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import datetime

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, get_datetime, get_link_to_form, getdate


class DeliveryTrip(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.delivery_stop.delivery_stop import DeliveryStop

		amended_from: DF.Link | None
		company: DF.Link
		delivery_stops: DF.Table[DeliveryStop]
		departure_time: DF.Datetime
		driver: DF.Link | None
		driver_address: DF.Link | None
		driver_email: DF.Data | None
		driver_name: DF.Data | None
		email_notification_sent: DF.Check
		employee: DF.Link | None
		naming_series: DF.Literal["MAT-DT-.YYYY.-"]
		status: DF.Literal["Draft", "Scheduled", "In Transit", "Completed", "Cancelled"]
		total_distance: DF.Float
		uom: DF.Link | None
		vehicle: DF.Link
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Google Maps returns distances in meters by default
		self.default_distance_uom = (
			frappe.db.get_single_value("Global Defaults", "default_distance_unit") or "Meter"
		)
		self.uom_conversion_factor = frappe.db.get_value(
			"UOM Conversion Factor", {"from_uom": "Meter", "to_uom": self.default_distance_uom}, "value"
		)

	def on_discard(self):
		self.update_status()
		self.update_delivery_notes(delete=True)

	def after_mapping(self, source_doc):
		for stop in self.delivery_stops[:]:
			if not any(stop.get(df.fieldname) for df in stop.meta.fields):
				self.remove(stop)

	def validate(self):
		if self._action == "submit" and not self.driver:
			frappe.throw(_("A driver must be set to submit."))

		if self._action == "submit":
			self.validate_delivery_note_not_draft()
		self.validate_delivery_notes_not_on_other_trips()
		self.validate_stop_addresses()

	def on_update(self):
		self.update_delivery_notes()
		self.release_removed_delivery_notes()

	def on_trash(self):
		self.update_delivery_notes(delete=True)

	def on_submit(self):
		self.update_status()

	def on_update_after_submit(self):
		self.update_status()

	def on_cancel(self):
		self.update_status()
		self.update_delivery_notes(delete=True)

	def validate_stop_addresses(self):
		for stop in self.delivery_stops:
			if stop.address and not stop.customer_address:
				stop.customer_address = get_address_display(frappe.get_doc("Address", stop.address).as_dict())

	def validate_delivery_note_not_draft(self):
		delivery_notes = list(set(stop.delivery_note for stop in self.delivery_stops if stop.delivery_note))
		draft_delivery_notes = frappe.get_all(
			"Delivery Note",
			{"docstatus": 0, "name": ["in", delivery_notes]},
			pluck="name",
		)
		if draft_delivery_notes:
			frappe.throw(
				_(
					"Delivery Notes should not be in draft state when submitting a Delivery Trip. The following Delivery Notes are still in draft state: {0}. Please submit them first."
				).format(", ".join(draft_delivery_notes))
			)

	def validate_delivery_notes_not_on_other_trips(self):
		delivery_notes = {stop.delivery_note for stop in self.delivery_stops if stop.delivery_note}
		if not delivery_notes:
			return

		delivery_note = frappe.qb.DocType("Delivery Note")
		notes = (
			frappe.qb.from_(delivery_note)
			.select(delivery_note.name, delivery_note.delivery_trip, delivery_note.company)
			.where(delivery_note.name.isin(delivery_notes))
			.for_update()
			.run(as_dict=True)
		)
		if other_company := [d.name for d in notes if self.company and d.company != self.company]:
			frappe.throw(
				_("Delivery Notes {0} do not belong to Company {1}").format(
					", ".join(other_company), frappe.bold(self.company)
				)
			)

		other_trips = {d.delivery_trip for d in notes if d.delivery_trip and d.delivery_trip != self.name}
		open_trips = other_trips and set(
			frappe.get_all(
				"Delivery Trip",
				filters={"name": ("in", list(other_trips)), "docstatus": ("<", 2)},
				pluck="name",
			)
		)
		if linked := [d for d in notes if open_trips and d.delivery_trip in open_trips]:
			frappe.throw(
				_("Delivery Notes are already on another Delivery Trip: {0}").format(
					", ".join(f"{d.name} ({d.delivery_trip})" for d in linked)
				)
			)

	def update_status(self):
		status = {0: "Draft", 1: "Scheduled", 2: "Cancelled"}[self.docstatus]

		if self.docstatus == 1:
			visited_stops = [stop.visited for stop in self.delivery_stops]
			if all(visited_stops):
				status = "Completed"
			elif any(visited_stops):
				status = "In Transit"

		self.db_set("status", status)

	def release_removed_delivery_notes(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		current = {stop.delivery_note for stop in self.delivery_stops}
		removed = {stop.delivery_note for stop in doc_before_save.delivery_stops if stop.delivery_note}
		if removed - current:
			self.update_delivery_notes(delete=True, delivery_notes=removed - current)

	def update_delivery_notes(self, delete=False, delivery_notes=None):
		if delivery_notes is None:
			delivery_notes = {stop.delivery_note for stop in self.delivery_stops if stop.delivery_note}
		if not delivery_notes:
			return

		trip_values = [self.get_delivery_note_values()]
		if doc_before_save := self.get_doc_before_save():
			trip_values.append(doc_before_save.get_delivery_note_values())

		updated = []
		for note in frappe.get_all(
			"Delivery Note",
			filters={"name": ("in", list(delivery_notes))},
			fields=["name", "delivery_trip", *trip_values[0]],
		):
			update = release_delivery_note if delete else link_delivery_note
			if values := update(note, self.name, trip_values):
				frappe.db.set_value("Delivery Note", note.name, values)
				updated.append(get_link_to_form("Delivery Note", note.name))

		if updated:
			frappe.msgprint(_("Delivery Notes {0} updated").format(", ".join(updated)))

	def get_delivery_note_values(self):
		return {
			"driver": self.driver,
			"driver_name": self.driver_name,
			"vehicle_no": self.vehicle,
			"lr_no": self.name,
			"lr_date": getdate(self.departure_time) if self.departure_time else None,
		}

	@frappe.whitelist()
	def process_route(self, optimize: bool):
		"""
		Estimate the arrival times for each stop in the Delivery Trip.
		If `optimize` is True, the stops will be re-arranged, based
		on the optimized order, before estimating the arrival times.

		Args:
		        optimize (bool): True if route needs to be optimized, else False
		"""

		departure_datetime = get_datetime(self.departure_time)
		route_list = self.form_route_list(optimize)
		ends_at_home = not (optimize and self.delivery_stops and self.delivery_stops[-1].locked)
		total_distance = None

		# For locks, maintain idx count while looping through route list
		idx = 0
		for route_idx, route in enumerate(route_list):
			directions = self.get_directions(route, optimize)

			if directions:
				if optimize and len(directions.get("waypoint_order")) > 1:
					self.rearrange_stops(directions.get("waypoint_order"), start=idx)

				# Avoid estimating last leg back to the home address
				legs = directions.get("legs")
				if ends_at_home and route_idx == len(route_list) - 1:
					legs = legs[:-1]

				# Google Maps returns the legs in the optimized order
				for leg in legs:
					delivery_stop = self.delivery_stops[idx]

					delivery_stop.lat, delivery_stop.lng = leg.get("end_location", {}).values()
					delivery_stop.uom = self.default_distance_uom
					distance = leg.get("distance", {}).get("value", 0.0)  # in meters
					delivery_stop.distance = distance * self.uom_conversion_factor

					duration = leg.get("duration", {}).get("value", 0)
					estimated_arrival = departure_datetime + datetime.timedelta(seconds=duration)
					delivery_stop.estimated_arrival = estimated_arrival

					stop_delay = frappe.db.get_single_value("Delivery Settings", "stop_delay")
					departure_datetime = estimated_arrival + datetime.timedelta(minutes=cint(stop_delay))
					idx += 1

				# Include last leg in the final distance calculation
				total_distance = flt(total_distance) + sum(
					leg.get("distance", {}).get("value", 0.0) for leg in directions.get("legs")
				)  # in meters
			else:
				idx += len(route) - 1

		if total_distance is not None:
			self.uom = self.default_distance_uom
			self.total_distance = total_distance * self.uom_conversion_factor

		self.save()

	def form_route_list(self, optimize):
		"""
		Form a list of address routes based on the delivery stops. If locks
		are present, and the routes need to be optimized, then they will be
		split into sublists at the specified lock position(s).

		Args:
		        optimize (bool): `True` if route needs to be optimized, else `False`

		Returns:
		        (list of list of str): List of address routes split at locks, if optimize is `True`
		"""
		if not self.driver_address:
			frappe.throw(_("Cannot calculate arrival time as the driver address is missing."))

		home_address = get_address_display(frappe.get_doc("Address", self.driver_address).as_dict())

		route_list = []
		# Initialize first leg with origin as the home address
		leg = [home_address]

		for stop in self.delivery_stops:
			leg.append(stop.customer_address)

			if optimize and stop.locked:
				route_list.append(leg)
				leg = [stop.customer_address]

		# For last leg, append home address as the destination
		# only if lock isn't on the final stop
		if len(leg) > 1:
			leg.append(home_address)
			route_list.append(leg)

		route_list = [[sanitize_address(address) for address in route] for route in route_list]

		return route_list

	def rearrange_stops(self, optimized_order, start):
		"""
		Re-arrange delivery stops based on order optimized
		for vehicle routing problems.

		Args:
		        optimized_order (list of int): The index-based optimized order of the route
		        start (int): The index at which to start the rearrangement
		"""

		stops_order = []

		# Child table idx starts at 1
		for new_idx, old_idx in enumerate(optimized_order, 1):
			new_idx = start + new_idx
			old_idx = start + old_idx

			self.delivery_stops[old_idx].idx = new_idx
			stops_order.append(self.delivery_stops[old_idx])

		self.delivery_stops[start : start + len(stops_order)] = stops_order

	def get_directions(self, route, optimize):
		"""
		Retrieve map directions for a given route and departure time.
		If optimize is `True`, Google Maps will return an optimized
		order for the intermediate waypoints.

		NOTE: Google's API does take an additional `departure_time` key,
		but it only works for routes without any waypoints.

		Args:
		        route (list of str): Route addresses (origin -> waypoint(s), if any -> destination)
		        optimize (bool): `True` if route needs to be optimized, else `False`

		Returns:
		        (dict): Route legs and, if `optimize` is `True`, optimized waypoint order
		"""
		if not frappe.db.get_single_value("Google Settings", "api_key"):
			frappe.throw(_("Enter API key in Google Settings."))

		import googlemaps

		try:
			maps_client = googlemaps.Client(key=frappe.db.get_single_value("Google Settings", "api_key"))
		except Exception as e:
			frappe.throw(e)

		directions_data = {
			"origin": route[0],
			"destination": route[-1],
			"waypoints": route[1:-1],
			"optimize_waypoints": optimize,
		}

		try:
			directions = maps_client.directions(**directions_data)
		except Exception as e:
			frappe.throw(_(str(e)))

		return directions[0] if directions else False


def is_trip_value(note, field, trip_values):
	return any(cstr(note.get(field)) == cstr(values[field]) for values in trip_values)


def link_delivery_note(note, trip_name, trip_values):
	values = {} if note.delivery_trip == trip_name else {"delivery_trip": trip_name}
	for field, value in trip_values[0].items():
		if note.get(field) != value and (not note.get(field) or is_trip_value(note, field, trip_values)):
			values[field] = value

	return values


def release_delivery_note(note, trip_name, trip_values):
	if note.delivery_trip != trip_name:
		return {}

	values = {"delivery_trip": None}
	for field in trip_values[0]:
		if note.get(field) and is_trip_value(note, field, trip_values):
			values[field] = None

	return values


@frappe.whitelist()
def get_contact_and_address(name: str):
	# `select`, not `read`: three of the four roles that run Delivery Trips hold no Customer read row
	frappe.has_permission("Customer", ptype="select", doc=name, throw=True)

	out = frappe._dict()

	get_default_contact(out, name)
	get_default_address(out, name)

	return out


def get_default_contact(out, name):
	dl = frappe.qb.DocType("Dynamic Link")
	contact = frappe.qb.DocType("Contact")
	contact_persons = (
		frappe.qb.from_(dl)
		.left_join(contact)
		.on(contact.name == dl.parent)
		.select(dl.parent, contact.is_primary_contact)
		.where((dl.link_doctype == "Customer") & (dl.link_name == name) & (dl.parenttype == "Contact"))
		.run(as_dict=1)
	)

	if contact_persons:
		for out.contact_person in contact_persons:
			if out.contact_person.is_primary_contact:
				return out.contact_person

		out.contact_person = contact_persons[0]

		return out.contact_person


def get_default_address(out, name):
	dl = frappe.qb.DocType("Dynamic Link")
	address = frappe.qb.DocType("Address")
	shipping_addresses = (
		frappe.qb.from_(dl)
		.left_join(address)
		.on(address.name == dl.parent)
		.select(dl.parent, address.is_shipping_address)
		.where((dl.link_doctype == "Customer") & (dl.link_name == name) & (dl.parenttype == "Address"))
		.run(as_dict=1)
	)

	if shipping_addresses:
		for out.shipping_address in shipping_addresses:
			if out.shipping_address.is_shipping_address:
				return out.shipping_address

		out.shipping_address = shipping_addresses[0]

		return out.shipping_address


@frappe.whitelist()
def get_contact_display(contact: str):
	if not frappe.has_permission("Contact", "read", doc=contact):
		check_contact_customer_permission(contact)

	contact_info = frappe.db.get_value(
		"Contact", contact, ["first_name", "last_name", "phone", "mobile_no"], as_dict=1
	)

	contact_info.html = """ <b>{first_name} {last_name}</b> <br> {phone} <br> {mobile_no}""".format(
		first_name=contact_info.first_name,
		last_name=contact_info.last_name or "",
		phone=contact_info.phone or "",
		mobile_no=contact_info.mobile_no or "",
	)

	return contact_info.html


def check_contact_customer_permission(contact):
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	customers = (
		frappe.qb.from_(dynamic_link)
		.select(dynamic_link.link_name)
		.where(
			(dynamic_link.parenttype == "Contact")
			& (dynamic_link.parent == contact)
			& (dynamic_link.link_doctype == "Customer")
		)
		.run(pluck=True)
	)
	if not any(frappe.has_permission("Customer", "select", doc=customer) for customer in customers):
		frappe.throw(_("Not permitted to view Contact {0}").format(contact), frappe.PermissionError)


def sanitize_address(address):
	"""
	Remove HTML breaks in a given address

	Args:
	        address (str): Address to be sanitized

	Returns:
	        (str): Sanitized address
	"""

	if not address:
		return

	address = address.split("<br>")

	# Only get the first 3 blocks of the address
	return ", ".join(address[:3])


@frappe.whitelist()
def notify_customers(delivery_trip: str):
	delivery_trip = frappe.get_doc("Delivery Trip", delivery_trip)
	delivery_trip.check_permission()

	dispatch_template_name = frappe.db.get_single_value("Delivery Settings", "dispatch_template")
	if not dispatch_template_name:
		frappe.throw(_("Missing email template for dispatch. Please set one in Delivery Settings."))

	dispatch_template = frappe.get_doc("Email Template", dispatch_template_name)
	context = delivery_trip.as_dict()

	if delivery_trip.driver:
		context.update(frappe.db.get_value("Driver", delivery_trip.driver, "cell_number", as_dict=1))

	email_recipients = []

	for stop in delivery_trip.delivery_stops:
		contact_info = frappe.db.get_value(
			"Contact", stop.contact, ["first_name", "last_name", "email_id"], as_dict=1
		)

		context.update({"items": []})
		if stop.delivery_note:
			items = frappe.get_all(
				"Delivery Note Item", filters={"parent": stop.delivery_note, "docstatus": 1}, fields=["*"]
			)
			context.update({"items": items})

		if contact_info and contact_info.email_id:
			context.update(stop.as_dict())
			context.update(contact_info)

			frappe.sendmail(
				recipients=contact_info.email_id,
				subject=dispatch_template.get_formatted_subject(context),
				message=dispatch_template.get_formatted_response(context),
				attachments=get_attachments(stop),
			)

			stop.db_set("email_sent_to", contact_info.email_id)
			email_recipients.append(contact_info.email_id)

	if email_recipients:
		frappe.msgprint(_("Email sent to {0}").format(", ".join(email_recipients)))
		delivery_trip.db_set("email_notification_sent", 1)
	else:
		frappe.msgprint(_("No contacts with email IDs found."))


def get_attachments(delivery_stop):
	if not (
		frappe.db.get_single_value("Delivery Settings", "send_with_attachment")
		and delivery_stop.delivery_note
	):
		return []

	dispatch_attachment = frappe.db.get_single_value("Delivery Settings", "dispatch_attachment")
	attachments = frappe.attach_print(
		"Delivery Note",
		delivery_stop.delivery_note,
		file_name="Delivery Note",
		print_format=dispatch_attachment,
	)

	return [attachments]


@frappe.whitelist()
def get_driver_email(driver: str):
	frappe.has_permission("Driver", "select", doc=driver, throw=True)

	employee = frappe.db.get_value("Driver", driver, "employee")
	email = frappe.db.get_value("Employee", employee, "prefered_email")
	return {"email": email}
