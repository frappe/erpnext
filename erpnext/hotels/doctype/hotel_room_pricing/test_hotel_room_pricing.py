# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

test_dependencies = ["Hotel Room Package"]
test_records = [
	dict(doctype="Hotel Room Pricing", enabled=1,
		name="Winter 2017",
		from_date="2017-01-01", to_date="2017-01-10",
		items = [
			dict(item="Basic Room with Breakfast", rate=10000),
			dict(item="Basic Room with Lunch", rate=11000),
			dict(item="Basic Room with Dinner", rate=12000)
		])
]

class TestHotelRoomPricing(unittest.TestCase):
	pass
