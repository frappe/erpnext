# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from operations import install_fixtures, taxes_setup, defaults_setup, company_setup, sample_data
from erpnext.setup.doctype.company.company import install_country_fixtures

def get_setup_stages(args=None):
	if frappe.db.sql("select name from tabCompany"):
		stages = [
			{
				'status': _('Wrapping up'),
				'fail_msg': _('Failed to login'),
				'tasks': [
					{
						'fn': fin,
						'args': args,
						'fail_msg': _("Failed to login")
					}
				]
			}
		]
	else:
		stages = [
			{
				'status': _('Installing presets'),
				'fail_msg': _('Failed to install presets'),
				'tasks': [
					{
						'fn': stage_fixtures,
						'args': args.get("country"),
					}
				]
			},
			{
				'status': _('Setting up company and taxes'),
				'fail_msg': _('Failed to setup company'),
				'tasks': [
					{
						'fn': setup_company,
						'args': args,
						'fail_msg': _("Failed to setup company")
					},
					{
						'fn': setup_taxes,
						'args': args,
						'fail_msg': _("Failed to setup taxes")
					}
				]
			},
			{
				'status': _('Setting defaults'),
				'fail_msg': 'Failed to set defaults',
				'tasks': [
					{
						'fn': stage_three,
						'args': args,
						'fail_msg': _("Failed to set defaults")
					}
				]
			},
			{
				'status': _('Making website'),
				'fail_msg': _('Failed to create website'),
				'tasks': [
					{
						'fn': stage_four,
						'args': args,
						'fail_msg': _("Failed to create website")
					}
				]
			},
			{
				'status': _('Wrapping up'),
				'fail_msg': _('Failed to login'),
				'tasks': [
					{
						'fn': fin,
						'args': args,
						'fail_msg': _("Failed to login")
					}
				]
			}
		]

	return stages

def setup_complete(args=None):
	stage_fixtures(args)
	setup_company(args)
	setup_taxes(args)
	stage_three(args)
	stage_four(args)
	fin(args)

def post_setup(args=None):
	install_country_fixtures(frappe.defaults.get_defaults().get("company"))

def stage_fixtures(country):
	return install_fixtures.install(country)

def setup_company(args):
	# set default customer group and territory
	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.set_default_customer_group_and_territory()
	selling_settings.save()

	domain_settings = frappe.get_single('Domain Settings')
	domain_settings.set_active_domains(args.get('domains'))
	domain_settings.save()

	variant_settings = frappe.get_doc('Item Variant Settings')
	variant_settings.set_default_fields()
	variant_settings.save()

	return company_setup.get_company_records(args)

def setup_taxes(args):
	return taxes_setup.create_sales_tax(args)

def stage_three(args):
	defaults_setup.create_employee_for_self(args)
	defaults_setup.set_default_settings(args)
	defaults_setup.create_territories()
	defaults_setup.create_feed_and_todo()

def stage_four(args):
	company_setup.create_logo(args)
	company_setup.create_website(args)
	return company_setup.get_email_digest()

def fin(args):
	frappe.local.message_log = []
	login_as_first_user(args)

	make_sample_data(args.get('domains'))

def make_sample_data(domains):
	try:
		sample_data.make_sample_data(domains)
	except:
		# clear message
		if frappe.message_log:
			frappe.message_log.pop()
		pass

def login_as_first_user(args):
	if args.get("email") and hasattr(frappe.local, "login_manager"):
		frappe.local.login_manager.login_as(args.get("email"))
