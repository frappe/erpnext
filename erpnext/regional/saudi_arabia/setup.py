# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from erpnext.regional.united_arab_emirates.setup import make_custom_fields, add_print_formats
from erpnext.setup.setup_wizard.operations.taxes_setup import create_sales_tax

def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()

	if company:
		create_sales_tax(company)