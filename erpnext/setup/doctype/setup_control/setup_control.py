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

import webnotes

from webnotes.utils import cint, cstr, flt, getdate, now, nowdate
from webnotes.model.doc import Document, addchild
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	#Default Naming Series
	#---------------------------------------------------
	def naming_series(self):
		ns = [['TDS Payment', 'TDSP'], ['Payable Voucher', 'BILL'], ['Journal Voucher', 'JV'], ['Receivable Voucher', 'INV'], ['Lead', 'Lead'], ['Indent', 'IDT'], ['Enquiry', 'Enquiry'], ['Purchase Order', 'PO'], ['Quotation', 'QTN'], ['Purchase Receipt', 'GRN'], ['Stock Entry', 'STE'], ['Sales Order', 'SO'], ['Delivery Note', 'DN'], ['Employee', 'EMP/']]
		for r in ns: 
			rec = Document('Naming Series')
			rec.select_doc_for_series = r[0]
			rec.new_series = r[1]
			rec_obj = get_obj(doc=rec)
			rec_obj.add_series()

	# set account details
	#-----------------------
	def set_account_details(self, args):
		"""
			Called from gateway after allocation
		"""
		import json
		args = json.loads(args)

		self.set_cp_defaults(args['company'], args['industry'], args['time_zone'], args['country'], args['account_name'])
		self.create_profile(args['user'], args['first_name'], args['last_name'], args.get('pwd'))	
	
		# Domain related updates
		try:
			from server_tools.gateway_utils import add_domain_map
			add_domain_map(args)
		except ImportError, e:
			pass

		# add record in domain_list of Website Settings
		webnotes.conn.set_value('Website Settings', 'Website Settings', 'subdomain', args['url_name'] + ".erpnext.com")
		
	
	# Account Setup
	# ---------------
	def setup_account(self, args):
		import webnotes, json
		locals().update(args)

		curr_fiscal_year, fy_start_date = self.get_fy_details(fy_start)
		self.currency = currency

		# Update Profile
		if last_name=='None': last_name = None
		webnotes.conn.sql("""\
			UPDATE `tabProfile` SET first_name=%s, last_name=%s
			WHERE name=%s AND docstatus<2""", (first_name, last_name, webnotes.user.name))
			
		
		# Fiscal Year
		master_dict = {'Fiscal Year':{'year':curr_fiscal_year, 'year_start_date':fy_start_date}}
		self.create_records(master_dict)
		
		# Company
		master_dict = {'Company':{'company_name':company_name,
								  'abbr':company_abbr,
								  'default_currency':currency
															}}
		self.create_records(master_dict)
		
		def_args = {'current_fiscal_year':curr_fiscal_year,
								'default_currency': currency,
								'default_company':company_name,
								'default_valuation_method':'FIFO',
								'default_stock_uom':'Nos',
								'date_format':'dd-mm-yyyy',
								'default_currency_format':'Lacs',
								'so_required':'No',
								'dn_required':'No',
								'po_required':'No',
								'pr_required':'No',
								'emp_created_by':'Naming Series',
								'cust_master_name':'Customer Name', 
								'supp_master_name':'Supplier Name',
								'default_currency_format': (currency=='INR') and 'Lacs' or 'Millions'
					}

		# Set 
		self.set_defaults(def_args)

		self.create_feed_and_todo()

		webnotes.clear_cache()
		msgprint("Company setup is complete")
		
		import webnotes.utils
		user_fullname = (first_name or '') + (last_name and (" " + last_name) or '')
		return {'sys_defaults': webnotes.utils.get_defaults(), 'user_fullname': user_fullname}

	def create_feed_and_todo(self):
		"""update activty feed and create todo for creation of item, customer, vendor"""
		import home
		home.make_feed('Comment', '', '', webnotes.session['user'],
			'<i>"' + doc.comment + '"</i>', '#6B24B3')

		d = Document('ToDo Item')
		d.description = 'Create your first <a href="#!List/Customer">Customer</a>'
		d.priority = 'High'
		d.date = nowdate()
		d.save(1)

		d = Document('ToDo Item')
		d.description = 'Create your first <a href="#!List/Item">Item</a>'
		d.priority = 'High'
		d.date = nowdate()
		d.save(1)

		d = Document('ToDo Item')
		d.description = 'Create your first <a href="#!List/Supplier">Supplier</a>'
		d.priority = 'High'
		d.date = nowdate()
		d.save(1)

		
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
		else:
			fy = cstr(curr_year) + '-' + cstr(curr_year+1)
		return fy,stdt


	# Create Company and Fiscal Year
	# ------------------------------- 
	def create_records(self, master_dict):
		for d in master_dict.keys():
			rec = Document(d)
			for fn in master_dict[d].keys():
				rec.fields[fn] = master_dict[d][fn]
			# add blank fields
			for fn in rec.fields:
				if fn not in master_dict[d].keys()+['name','owner','doctype']:
					rec.fields[fn] = ''
			rec_obj = get_obj(doc=rec)
			rec_obj.doc.save(1)
			if hasattr(rec_obj, 'on_update'):
				rec_obj.on_update()


	# Set System Defaults
	# --------------------
	def set_defaults(self, def_args):
		ma_obj = get_obj('Manage Account','Manage Account')
		for d in def_args.keys():
			ma_obj.doc.fields[d] = def_args[d]
		ma_obj.doc.save()
		ma_obj.on_update()


	# Set Control Panel Defaults
	# --------------------------
	def set_cp_defaults(self, cname, industry, timezone, country, acc_name):
		cp = Document('Control Panel','Control Panel')
		cp.account_id = acc_name
		cp.company_name = cname
		cp.industry = industry
		cp.time_zone = timezone
		cp.country = country
		cp.client_name = '<div style="padding:4px; font-size:20px;">'+cname+'</div>'
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
		if pwd: webnotes.conn.sql("UPDATE `tabProfile` SET password=PASSWORD(%s) WHERE name=%s", (pwd, user_email))
		self.add_roles(pr)
	
	def add_roles(self, pr):
		roles_list = ['Accounts Manager', 'Accounts User', 'Blogger', 'HR Manager', 'HR User', 'Maintenance User', 'Maintenance Manager', 'Material Manager', 'Material User', 'Material Master Manager', 'Production Manager', 'Production User', 'Projects User', 'Purchase Manager', 'Purchase User', 'Purchase Master Manager', 'Quality Manager', 'Sales Manager', 'Sales User', 'Sales Master Manager', 'Support Manager', 'Support Team', 'System Manager', 'Website Manager']
		for r in roles_list:
			d = addchild(pr, 'userroles', 'UserRole', 1)
			d.role = r
			d.save(1)

		# Add roles to Administrator profile
		pr = Document('Profile','Administrator')
		for r in roles_list:
			d = addchild(pr,'userroles', 'UserRole', 1)
			d.role = r
			d.save(1)
		
	
	def is_setup_okay(self, args):
		"""
		Validates if setup has been performed after database allocation
		"""

		from server_tools.gateway_utils import get_total_users
		
		args = eval(args)		
		cp_defaults = webnotes.conn.get_value('Control Panel', None, 'account_id')
		user_profile = webnotes.conn.get_value('Profile', args['user'], 'name')
		
		from webnotes.utils import cint
		
		total_users = get_total_users()
						
		if (cp_defaults==args['account_name']) and user_profile and \
		   (total_users==cint(args['total_users'])):
		   return 'True'
		
