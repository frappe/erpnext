# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
test_dependencies = ["Hotel Room Pricing", "Hotel Room"]

class TestHotelRoomReservation(unittest.TestCase):
	def test_reservation(self):
		reservation = make_reservation(
			from_date="2017-01-01",
			to_date="2017-01-03",
			items=[
				dict(item="Basic Room with Dinner", qty=2)
			]
		)
		reservation.insert()
		self.assertEqual(reservation.net_total, 48000)

def make_reservation(**kwargs):
	kwargs["doctype"] = "Hotel Room Reservation"
	if not "guest_name" in kwargs:
		kwargs["guest_name"] = "Test Guest"
	doc = frappe.get_doc(kwargs)
	return doc
