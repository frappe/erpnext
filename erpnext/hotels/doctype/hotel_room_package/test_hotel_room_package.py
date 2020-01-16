# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
test_records = [
	dict(doctype='Item', item_code='Breakfast',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='Lunch',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='Dinner',
		item_group='Products', is_stock_item=0),
	dict(doctype='Item', item_code='WiFi',
		item_group='Products', is_stock_item=0),
	dict(doctype='Hotel Room Type', name="Delux Room",
		capacity=4,
		extra_bed_capacity=2,
		amenities = [
			dict(item='WiFi', billable=0)
		]),
	dict(doctype='Hotel Room Type', name="Basic Room",
		capacity=4,
		extra_bed_capacity=2,
		amenities = [
			dict(item='Breakfast', billable=0)
		]),
	dict(doctype="Hotel Room Package", name="Basic Room with Breakfast",
		hotel_room_type="Basic Room",
		amenities = [
			dict(item="Breakfast", billable=0)
		]),
	dict(doctype="Hotel Room Package", name="Basic Room with Lunch",
		hotel_room_type="Basic Room",
		amenities = [
			dict(item="Breakfast", billable=0),
			dict(item="Lunch", billable=0)
		]),
	dict(doctype="Hotel Room Package", name="Basic Room with Dinner",
		hotel_room_type="Basic Room",
		amenities = [
			dict(item="Breakfast", billable=0),
			dict(item="Dinner", billable=0)
		])
]

class TestHotelRoomPackage(unittest.TestCase):
	pass
