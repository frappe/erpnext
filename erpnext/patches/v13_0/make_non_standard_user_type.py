# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from erpnext.setup.install import add_non_standard_user_types

def execute():
	add_non_standard_user_types()