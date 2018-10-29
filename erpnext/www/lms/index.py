from __future__ import unicode_literals
import frappe
import erpnext.education.utils as utils

def get_context(context):
    context.featured = utils.get_featured_programs()
    context.settings = frappe.get_doc("Education Settings")