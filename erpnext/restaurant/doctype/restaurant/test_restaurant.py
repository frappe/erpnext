# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

test_records = [
	dict(doctype='Restaurant', name='Test Restaurant 1', company='_Test Company 1',
		invoice_series_prefix='Test-Rest-1-Inv-'),
	dict(doctype='Restaurant', name='Test Restaurant 2', company='_Test Company 1',
		invoice_series_prefix='Test-Rest-2-Inv-'),
]

class TestRestaurant(unittest.TestCase):
	pass
