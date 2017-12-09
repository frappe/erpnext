# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, add_days, flt

class HotelRoomReservation(Document):
	def validate(self):
		self.total_rooms = {}
		self.rooms_booked = {}
		self.validate_availability()

	def validate_availability(self):
		for d in self.items:
			if not d.item in self.rooms_booked:
				self.rooms_booked[d.item] = 0
			for i in xrange(date_diff(self.to_date, self.from_date)):
				day = add_days(self.from_date, i)
				rooms_booked = self.get_rooms_booked(d.item, day) + d.qty + self.rooms_booked.get(d.item)
				total_rooms = self.get_total_rooms(d.item)
				if total_rooms < rooms_booked:
					frappe.throw(_("Hotel Rooms of type {0} are unavailable on {1}".format(d.item,
						frappe.format(day, dict(fieldtype="Date")))))
				self.rooms_booked[d.item] += rooms_booked

	def get_rooms_booked(self, item, day):
		return frappe.db.sql("""
			select sum(item.qty)
			from
				`tabHotel Room Reservation Item` item,
				`tabHotel Room Reservation` reservation
			where
				item.parent = reservation.name
				and item.item = %s
				and reservation.docstatus = 1
				and reservation.name != %s
				and %s between reservation.from_date
					and reservation.to_date""", (item, self.name, day))[0][0]

	def get_total_rooms(self, item):
		if not item in self.total_rooms:
			self.total_rooms[item] = frappe.db.sql("""
				select count(*)
				from
					`tabHotel Room Package` package
				inner join
					`tabHotel Room` room on package.hotel_room_type = room.hotel_room_type
				where
					package.item = %s""", item)[0][0]

		return self.total_rooms[item]

@frappe.whitelist()
def get_room_rate(hotel_room_reservation):
	"""Calculate rate for each day as it may belong to different Hotel Room Pricing Item"""
	doc = json.loads(hotel_room_reservation)
	doc["net_total"] = 0
	for d in doc.get("items"):
		net_rate = 0.0
		for i in xrange(date_diff(doc.get("to_date"), doc.get("from_date"))):
			day = add_days(doc.get("from_date"), i)
			if not d.get("item"):
				continue
			day_rate = frappe.db.sql("""
				select 
					item.rate 
				from 
					`tabHotel Room Pricing Item` item,
					`tabHotel Room Pricing` pricing
				where
					item.parent = pricing.name
					and item.item = %s
					and %s between pricing.from_date 
						and pricing.to_date""", (d.get("item"), day))

			if day_rate:
				net_rate += day_rate[0][0]
			else:
				frappe.throw(
					_("Please set Hotel Room Rate on {}".format(
						frappe.format(day, dict(fieldtype="Date")))))
		d["rate"] = net_rate
		d["amount"] = net_rate * flt(d.get("qty"))
		doc["net_total"] += d["amount"]
	return doc
