# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.regional.italy.setup import make_custom_fields

def execute():
    make_custom_fields()
