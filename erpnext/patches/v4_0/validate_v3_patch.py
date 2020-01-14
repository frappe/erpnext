# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	from frappe.modules.patch_handler import executed
	last_v3_patch = 'patches.1401.fix_pos_outstanding'
	if not executed(last_v3_patch):
		raise Exception("site not ready to migrate to version 4")
