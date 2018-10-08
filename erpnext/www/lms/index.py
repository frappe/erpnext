from __future__ import unicode_literals
import frappe

def get_context(context):
    context.featured = frappe.get_all('Program', filters={'is_featured': 1}, fields=['program_name', 'program_code', 'description', 'hero_image'])