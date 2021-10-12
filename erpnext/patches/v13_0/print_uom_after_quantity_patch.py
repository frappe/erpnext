# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from erpnext.setup.install import create_print_uom_after_qty_custom_field


def execute():
    create_print_uom_after_qty_custom_field()
