# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import erpnext

def execute():
	"""Create domain documents"""
	frappe.reload_doc("core", "doctype", "domain")
	frappe.reload_doc("core", "doctype", "domain_settings")
	frappe.reload_doc("core", "doctype", "has_domain")
	frappe.reload_doc("core", "doctype", "role")

	for domain in ("Distribution", "Manufacturing", "Retail", "Services", "Education"):
		if not frappe.db.exists({"doctype": "Domain", "domain": domain}):
			create_domain(domain)

	# set domain in domain settings based on company domain

	domains = []
	condition = ""
	company = erpnext.get_default_company()
	if company:
		condition = " and name='{0}'".format(frappe.db.escape(company))

	domains = frappe.db.sql_list("select distinct domain from `tabCompany` where domain != 'Other' {0}".format(condition))

	if not domains:
		return

	domain_settings = frappe.get_doc("Domain Settings", "Domain Settings")
	checked_domains = [row.domain for row in domain_settings.active_domains]

	for domain in domains:
		# check and ignore if the domains is already checked in domain settings
		if domain in checked_domains:
			continue

		if not frappe.db.get_value("Domain", domain):
			# user added custom domain in companies domain field
			create_domain(domain)

		row = domain_settings.append("active_domains", dict(domain=domain))

	domain_settings.save(ignore_permissions=True)

def create_domain(domain):
	# create new domain

	doc = frappe.new_doc("Domain")
	doc.domain = domain
	doc.db_update()