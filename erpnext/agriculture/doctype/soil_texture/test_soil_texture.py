# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


class TestSoilTexture(unittest.TestCase):
	def test_texture_selection(self):
		soil_tex = frappe.get_all('Soil Texture', fields=['name'], filters={'collection_datetime': '2017-11-08'})
		doc = frappe.get_doc('Soil Texture', soil_tex[0].name)
		self.assertEqual(doc.silt_composition, 50)
		self.assertEqual(doc.soil_type, 'Silt Loam')
