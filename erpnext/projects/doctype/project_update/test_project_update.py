# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe


class TestProjectUpdate(unittest.TestCase):
	pass

test_records = frappe.get_test_records('Project Update')
test_ignore = ["Sales Order"]
