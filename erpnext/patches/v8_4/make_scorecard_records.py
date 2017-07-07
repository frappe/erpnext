# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_install_records
def execute():

	make_install_records()