# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.core.doctype.module_def.module_def import enable_module

def setup_non_profit():
	enable_module("Non Profit")