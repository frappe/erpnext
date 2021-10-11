# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

test_records = [
	dict(restaurant='Test Restaurant 1', no_of_seats=5, minimum_seating=1),
	dict(restaurant='Test Restaurant 1', no_of_seats=5, minimum_seating=1),
	dict(restaurant='Test Restaurant 1', no_of_seats=5, minimum_seating=1),
	dict(restaurant='Test Restaurant 1', no_of_seats=5, minimum_seating=1),
]

class TestRestaurantTable(unittest.TestCase):
	pass
