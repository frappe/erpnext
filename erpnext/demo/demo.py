from __future__ import unicode_literals

import frappe, sys
import erpnext
import frappe.utils
from erpnext.demo.setup_data import setup_data
from erpnext.demo.user import hr, sales, purchase, manufacturing, stock, accounts, projects, fixed_asset

"""
Make a demo

1. Start with a fresh account

bench --site demo.erpnext.dev reinstall

2. Install Demo

bench --site demo.erpnext.dev execute erpnext.demo.demo.make

3. If Demo breaks, to continue

bench --site demo.erpnext.dev execute erpnext.demo.demo.simulate

"""

def make(domain='Manufacturing'):
	frappe.flags.domain = domain
	frappe.flags.mute_emails = True
	setup_data()
	site = frappe.local.site
	frappe.destroy()
	frappe.init(site)
	frappe.connect()
	simulate()

def simulate():
	runs_for = frappe.flags.runs_for or 150
	frappe.flags.company = erpnext.get_default_company()
	frappe.flags.mute_emails = True

	if not frappe.flags.start_date:
		# start date = 100 days back
		frappe.flags.start_date = frappe.utils.add_days(frappe.utils.nowdate(), -1 * runs_for)

	current_date = frappe.utils.getdate(frappe.flags.start_date)

	# continue?
	demo_last_date = frappe.db.get_global('demo_last_date')
	if demo_last_date:
		current_date = frappe.utils.add_days(demo_last_date, 1)

	# run till today
	if not runs_for:
		runs_for = frappe.utils.date_diff(frappe.utils.nowdate(), current_date)
		# runs_for = 100
		
	fixed_asset.work()

	for i in xrange(runs_for):
		sys.stdout.write("\rSimulating {0}".format(current_date.strftime("%Y-%m-%d")))
		sys.stdout.flush()
		frappe.flags.current_date = current_date

		if current_date.weekday() in (5, 6):
			current_date = frappe.utils.add_days(current_date, 1)
			continue

		hr.work()
		sales.work()
		purchase.work()
		manufacturing.work()
		stock.work()
		accounts.work()
		projects.run_projects(current_date)
		# run_stock()
		# run_accounts()
		# run_projects()
		# run_messages()

		current_date = frappe.utils.add_days(current_date, 1)

		frappe.db.commit()
