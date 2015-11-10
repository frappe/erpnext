# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
from frappe.website.utils import get_full_index

def get_context(context):
	context.full_index = get_full_index(extn = True)
