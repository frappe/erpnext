from __future__ import unicode_literals
import frappe

no_cache = 1
no_sitemap = 1

def get_context(context):
    context.blogs = frappe.get_all('Blog Post',
        fields=['title', 'blogger', 'blog_intro', 'route'],
        filters={
            'published': 1
        },
        order_by='modified desc',
        limit=3
    )

    context.homepage_settings = frappe.get_doc('Homepage', 'Homepage')
    context.get_item_route = get_item_route

    # homepage_sections = frappe.get_all('Homepage Section', order_by='section_order asc')
    # context.custom_sections = [frappe.get_doc('Homepage Section', name) for name in homepage_sections]

    context.explore_link = '/products'

    context.email = frappe.db.get_single_value('Contact Us Settings', 'email_id')
    context.phone = frappe.db.get_single_value('Contact Us Settings', 'phone')

    return context

def get_item_route(item_code):
    return frappe.db.get_value('Item', item_code, 'route')