# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
test_dependencies = ["Hotel Room Package"]
test_records = [
	dict(doctype="Hotel Room", name="1001",
		hotel_room_type="Basic Room"),
	dict(doctype="Hotel Room", name="1002",
		hotel_room_type="Basic Room"),
	dict(doctype="Hotel Room", name="1003",
		hotel_room_type="Basic Room"),
	dict(doctype="Hotel Room", name="1004",
		hotel_room_type="Basic Room"),
	dict(doctype="Hotel Room", name="1005",
		hotel_room_type="Basic Room"),
	dict(doctype="Hotel Room", name="1006",
		hotel_room_type="Basic Room")
]

class TestHotelRoom(unittest.TestCase):
	pass
