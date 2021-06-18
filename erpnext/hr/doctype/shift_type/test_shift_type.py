# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestShiftType(unittest.TestCase):
	pass

def create_shift_type():
	shift_type = frappe.new_doc("Shift Type")
	shift_type.name = "test shift"
	shift_type.start_time = "9:00:00"
	shift_type.end_time = "18:00:00"
	shift_type.enable_auto_attendance = 1

	shift_type.save()
	return shift_type
