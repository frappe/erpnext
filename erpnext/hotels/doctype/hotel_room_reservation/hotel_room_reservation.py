# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe import _
from frappe.utils import date_diff, add_days, flt

class HotelRoomReservation(Document):
	pass

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
				print("-"*40,d)
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
