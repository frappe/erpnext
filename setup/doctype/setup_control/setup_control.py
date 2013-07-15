# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr, getdate, now, nowdate
from webnotes.model.doc import Document, addchild
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	# Account Setup
	# ---------------
	def setup_account(self, args):
		import webnotes, json
		args = json.loads(args)
		webnotes.conn.begin()

		curr_fiscal_year, fy_start_date, fy_abbr = self.get_fy_details(args.get('fy_start'))
		#webnotes.msgprint(self.get_fy_details(args.get('fy_start')))

		args['name'] = webnotes.session.get('user')

		# Update Profile
		if not args.get('last_name') or args.get('last_name')=='None': args['last_name'] = None
		webnotes.conn.sql("""\
			UPDATE `tabProfile` SET first_name=%(first_name)s,
			last_name=%(last_name)s
			WHERE name=%(name)s AND docstatus<2""", args)
			
		
		# Fiscal Year
		master_dict = {'Fiscal Year':{
			'year': curr_fiscal_year,
			'year_start_date': fy_start_date,
		}}
		self.create_records(master_dict)
		
		
		# Company
		master_dict = {'Company': {
			'company_name':args.get('company_name'),
			'abbr':args.get('company_abbr'),
			'default_currency':args.get('currency')
		}}
		self.create_records(master_dict)

		# enable default currency
		webnotes.conn.set_value("Currency", args.get("currency"), "enabled", 1)

		
		def_args = {
			'current_fiscal_year':curr_fiscal_year,
			'default_currency': args.get('currency'),
			'default_company':args.get('company_name'),
			'default_valuation_method':'FIFO',
			'default_stock_uom':'Nos',
			'date_format': webnotes.conn.get_value("Country", 
				args.get("country"), "date_format"),
			'so_required':'No',
			'dn_required':'No',
			'po_required':'No',
			'pr_required':'No',
			'emp_created_by':'Naming Series',
			'cust_master_name':'Customer Name', 
			'supp_master_name':'Supplier Name'
		}

		# Set 
		self.set_defaults(def_args)
		
		cp_args = {}
		for k in ['industry', 'country', 'timezone', 'company_name']:
			cp_args[k] = args[k]
		
		self.set_cp_defaults(**cp_args)

		self.create_feed_and_todo()
		
		self.create_email_digest()

		webnotes.clear_cache()
		msgprint("Company setup is complete. This page will be refreshed in a moment.")
		
		import webnotes.utils
		user_fullname = (args.get('first_name') or '') + (args.get('last_name')
				and (" " + args.get('last_name')) or '')
		webnotes.conn.commit()
		return {'sys_defaults': webnotes.utils.get_defaults(), 'user_fullname': user_fullname}

	def create_feed_and_todo(self):
		"""update activty feed and create todo for creation of item, customer, vendor"""
		import home
		home.make_feed('Comment', 'ToDo', '', webnotes.session['user'],
			'<i>"' + 'Setup Complete. Please check your <a href="#!todo">\
			To Do List</a>' + '"</i>', '#6B24B3')

		d = Document('ToDo')
		d.description = 'Create your first Customer'
		d.priority = 'High'
		d.date = nowdate()
		d.reference_type = 'Customer'
		d.save(1)

		d = Document('ToDo')
		d.description = 'Create your first Item'
		d.priority = 'High'
		d.date = nowdate()
		d.reference_type = 'Item'
		d.save(1)

		d = Document('ToDo')
		d.description = 'Create your first Supplier'
		d.priority = 'High'
		d.date = nowdate()
		d.reference_type = 'Supplier'
		d.save(1)

	def create_email_digest(self):
		"""
			create a default weekly email digest
			* Weekly Digest
			* For all companies
			* Recipients: System Managers
			* Full content
			* Enabled by default
		"""
		import webnotes
		companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)

		from webnotes.profile import get_system_managers
		system_managers = get_system_managers()
		if not system_managers: return
		
		from webnotes.model.doc import Document
		for company in companies_list:
			if company and company[0]:
				edigest = Document('Email Digest')
				edigest.name = "Default Weekly Digest - " + company[0]
				edigest.company = company[0]
				edigest.frequency = 'Weekly'
				edigest.recipient_list = "\n".join(system_managers)
				for f in ['new_leads', 'new_enquiries', 'new_quotations',
						'new_sales_orders', 'new_purchase_orders',
						'new_transactions', 'payables', 'payments',
						'expenses_booked', 'invoiced_amount', 'collections',
						'income', 'bank_balance', 'stock_below_rl',
						'income_year_to_date', 'enabled']:
					edigest.fields[f] = 1
				exists = webnotes.conn.sql("""\
					SELECT name FROM `tabEmail Digest`
					WHERE name = %s""", edigest.name)
				if (exists and exists[0]) and exists[0][0]:
					continue
				else:
					edigest.save(1)
		
	# Get Fiscal year Details
	# ------------------------
	def get_fy_details(self, fy_start):
		st = {'1st Jan':'01-01','1st Apr':'04-01','1st Jul':'07-01', '1st Oct': '10-01'}
		curr_year = getdate(nowdate()).year
		if cint(getdate(nowdate()).month) < cint((st[fy_start].split('-'))[0]):
			curr_year = getdate(nowdate()).year - 1
		stdt = cstr(curr_year)+'-'+cstr(st[fy_start])
		#eddt = sql("select DATE_FORMAT(DATE_SUB(DATE_ADD('%s', INTERVAL 1 YEAR), INTERVAL 1 DAY),'%%d-%%m-%%Y')" % (stdt.split('-')[2]+ '-' + stdt.split('-')[1] + '-' + stdt.split('-')[0]))
		if(fy_start == '1st Jan'):
			fy = cstr(getdate(nowdate()).year)
			abbr = cstr(fy)[-2:]
		else:
			fy = cstr(curr_year) + '-' + cstr(curr_year+1)
			abbr = cstr(curr_year)[-2:] + '-' + cstr(curr_year+1)[-2:]
		return fy, stdt, abbr


	def create_records(self, master_dict):
		for d in master_dict.keys():
			rec = Document(d)
			for fn in master_dict[d].keys():
				rec.fields[fn] = master_dict[d][fn]
				
			rec_obj = get_obj(doc=rec)
			rec_obj.doc.save(1)
			if hasattr(rec_obj, 'on_update'):
				rec_obj.on_update()


	# Set System Defaults
	# --------------------
	def set_defaults(self, def_args):
		ma_obj = get_obj('Global Defaults','Global Defaults')
		for d in def_args.keys():
			ma_obj.doc.fields[d] = def_args[d]
		ma_obj.doc.save()
		ma_obj.on_update()


	# Set Control Panel Defaults
	# --------------------------
	def set_cp_defaults(self, industry, country, timezone, company_name):
		cp = Document('Control Panel','Control Panel')
		cp.company_name = company_name
		cp.industry = industry
		cp.time_zone = timezone
		cp.country = country
		cp.save()
			
	# Create Profile
	# --------------
	def create_profile(self, user_email, user_fname, user_lname, pwd=None):
		pr = Document('Profile')
		pr.first_name = user_fname
		pr.last_name = user_lname
		pr.name = pr.email = user_email
		pr.enabled = 1
		pr.save(1)
		if pwd:
			webnotes.conn.sql("""insert into __Auth (user, `password`) 
				values (%s, password(%s)) 
				on duplicate key update `password`=password(%s)""", 
				(user_email, pwd, pwd))
				
		add_all_roles_to(pr.name)
				
def add_all_roles_to(name):
	profile = webnotes.doc("Profile", name)
	for role in webnotes.conn.sql("""select name from tabRole"""):
		if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner"]:
			d = profile.addchild("userroles", "UserRole")
			d.role = role[0]
			d.insert()