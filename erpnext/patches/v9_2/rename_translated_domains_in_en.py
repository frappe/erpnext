from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc

def execute():
	frappe.reload_doc('stock', 'doctype', 'item')
	language = frappe.get_single("System Settings").language

	if language and language.startswith('en'): return

	frappe.local.lang = language

	all_domains = frappe.get_hooks("domains")

	for domain in all_domains:
		translated_domain = _(domain, lang=language)
		if frappe.db.exists("Domain", translated_domain):
			#if domain already exists merged translated_domain and domain
			merge = False
			if frappe.db.exists("Domain", domain):
				merge=True

			rename_doc("Domain", translated_domain, domain, ignore_permissions=True, merge=merge)

	domain_settings = frappe.get_single("Domain Settings")
	active_domains = [d.domain for d in domain_settings.active_domains]

	try:
		for domain in active_domains:
			domain = frappe.get_doc("Domain", domain)
			domain.setup_domain()

			if int(frappe.db.get_single_value('System Settings', 'setup_complete')):
				domain.setup_sidebar_items()
				domain.setup_desktop_icons()
				domain.set_default_portal_role()
	except frappe.LinkValidationError:
		pass