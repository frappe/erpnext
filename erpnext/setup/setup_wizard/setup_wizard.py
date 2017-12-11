# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from operations import install_fixtures, taxes_setup, defaults_setup, company_setup, sample_data

def setup_complete(args=None):
	stages = [
		{
			'status': 'Installing fixtures',
			'error': 'Errored in stage 1',
			'tasks': [
				{
					'f': stage_fixtures,
					'args': args,
					'error_msg': "Failed stage one"
				}
			]
		},
		{
			'status': 'Setting up company and taxes',
			'error': 'Errored in stage 1',
			'tasks': [
				{
					'f': stage_two,
					'args': args,
					'error_msg': "Failed stage one"
				}
			]
		},
		{
			'status': 'Setting defaults',
			'error': 'errored in stage Two',
			'tasks': [
				{
					'f': stage_three,
					'args': args,
					'error_msg': "Failed Stage two"
				}
			]
		},
		{
			'status': 'Making website',
			'error': 'errored in stage Three',
			'tasks': [
				{
					'f': stage_four,
					'args': args,
					'error_msg': "Failed Stage two"
				}
			]
		},
		{
			'status': 'Wrapping up',
			'error': 'errored in stage Two',
			'tasks': [
				{
					'f': fin,
					'args': args,
					'error_msg': "Failed fin"
				}
			]
		}
	]

	return stages


# def setup_complete(args=None):
# 	stage_fixtures(args)
# 	stage_two(args)
# 	stage_three(args)
# 	stage_four(args)
# 	fin(args)

def stage_fixtures(args):
	if frappe.db.sql("select name from tabCompany"):
		frappe.throw(_("Setup Already Complete!!"))

	install_fixtures.install(args.get("country"))

def stage_two(args):
	defaults_setup.create_price_lists(args)
	company_setup.create_fiscal_year_and_company(args)
	company_setup.enable_shopping_cart(args)
	company_setup.create_bank_account(args)
	taxes_setup.create_sales_tax(args)

def stage_three(args):
	defaults_setup.create_employee_for_self(args)
	defaults_setup.set_default_settings(args)
	defaults_setup.create_territories()
	defaults_setup.create_feed_and_todo()
	defaults_setup.set_no_copy_fields_in_variant_settings()

def stage_four(args):
	company_setup.create_website(args)
	company_setup.create_email_digest()
	company_setup.create_logo(args)

def fin(args):
	frappe.local.message_log = []
	frappe.db.commit()
	login_as_first_user(args)
	frappe.db.commit()
	frappe.clear_cache()

	make_sample_data(args.get('domains'))

def make_sample_data(domains):
	try:
		sample_data.make_sample_data(domains)
		frappe.clear_cache()
	except:
		# clear message
		if frappe.message_log:
			frappe.message_log.pop()
		pass

def login_as_first_user(args):
	if args.get("email") and hasattr(frappe.local, "login_manager"):
		frappe.local.login_manager.login_as(args.get("email"))
