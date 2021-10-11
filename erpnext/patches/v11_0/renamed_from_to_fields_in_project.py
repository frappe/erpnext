# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
    frappe.reload_doc('projects', 'doctype', 'project')

    if frappe.db.has_column('Project', 'from'):
        rename_field('Project', 'from', 'from_time')
        rename_field('Project', 'to', 'to_time')
