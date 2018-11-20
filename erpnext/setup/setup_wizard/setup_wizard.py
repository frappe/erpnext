# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import json
from time import time
from frappe import _

from .operations import install_fixtures as fixtures, taxes_setup, company_setup, sample_data

from frappe import _, _dict
from frappe.utils import cstr, getdate
from argparse import Namespace
from frappe.desk.page.setup_wizard.setup_wizard import update_global_settings, run_post_setup_complete, make_records
from journeys.journeys.config import get_journeys_config

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
						'args': args,
						'fail_msg': _("Failed to install presets")
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
						'fn': setup_post_company_fixtures,
						'args': args,
						'fail_msg': _("Failed to setup post company fixtures")
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
	setup_post_company_fixtures(args)
	fin(args)

def stage_fixtures(args):
	fixtures.install(args.get('country'))

def setup_company(args):
	fixtures.install_company(args)

def setup_taxes(args):
	taxes_setup.create_sales_tax(args)

def setup_post_company_fixtures(args):
	fixtures.install_post_company_fixtures(args)

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

@frappe.whitelist()
def install_fixtures():
	config = get_journeys_config().get('setup_config') or {}

	update_global_settings(_dict(config))

	fixtures.install(_dict(config).country)

@frappe.whitelist()
def make_setup_docs(args):
	config = get_journeys_config().get('setup_config') or {}

	args = json.loads(args)

	args.update(config)

	fixtures.install_company(_dict(args))
	fixtures.install_defaults(_dict(args))

	run_post_setup_complete(args)

@frappe.whitelist()
def setup(args, config=None):
	install_fixtures()
	make_setup_docs(args)
