# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from erpnext.regional.united_arab_emirates.setup import add_print_formats, make_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()
