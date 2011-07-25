# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


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
		args = eval(args)

		self.set_cp_defaults(args['company'], args['industry'], args['time_zone'], args['country'], args['account_name'])
		self.create_profile(args['user'], args['first_name'], args['last_name'])	
	
		from server_tools.gateway_utils import update_client_control
		update_client_control(args['total_users'])
		
	
	# Account Setup
	# ---------------
	def setup_account(self, args):
		company_name, comp_abbr, fy_start, currency = eval(args)
		curr_fiscal_year,fy_start_date = self.get_fy_details(fy_start)
		self.currency = currency
		
		# Fiscal Year
		master_dict = {'Fiscal Year':{'year':curr_fiscal_year,
																	'year_start_date':fy_start_date}}
		self.create_records(master_dict)
		
		# Company
		master_dict = {'Company':{'company_name':company_name,
								  'abbr':comp_abbr,
								  'default_currency':currency
															}}
		self.create_records(master_dict)
		
		def_args = {'current_fiscal_year':curr_fiscal_year,
								'default_currency': currency,
								'default_company':company_name,
								'default_valuation_method':'FIFO',
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

		# Set Registration Complete
		set_default('registration_complete','1')

		import webnotes.utils
		return webnotes.utils.get_defaults()

		
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
		ma_obj.update_cp()


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
	def create_profile(self, user_email, user_fname, user_lname):
		pr = Document('Profile')
		pr.first_name = user_fname
		pr.last_name = user_lname
		pr.name = pr.email = user_email
		pr.enabled = 1
		pr.save(1)
		self.add_roles(pr)
	
	def add_roles(self, pr):
		roles_list = ['System Manager','Sales Manager','Sales User','Purchase Manager','Purchase User','Material Manager','Material User','Accounts Manager','Accounts User','HR Manager','HR User','Production Manager','Production User','Sales Master Manager','Purchase Master Manager','Material Master Manager','Quality Manager','Maintenance User','Maintenance Manager']
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
			

	# Sync DB
	# -------
	def sync_db(arg=''):
		import webnotes.model.db_schema
		sql("delete from `tabDocType Update Register`")
		webnotes.model.db_schema.sync_all()
		
	
	def is_setup_okay(self, args):
		"""
		Validates if setup has been performed after database allocation
		"""

		from server_tools.gateway_utils import get_total_users
		
		args = eval(args)
		#webnotes.logger.error("args in set_account_details of setup_control: " + str(args))
		
		cp_defaults = webnotes.conn.get_value('Control Panel', None, 'account_id')
		
		user_profile = webnotes.conn.get_value('Profile', args['user'], 'name')
		
		from webnotes.utils import cint
		
		total_users = get_total_users()
		
		#webnotes.logger.error("setup_control.is_setup_okay: " + cp_defaults + " " + user_profile + " " + str(total_users))
		
		#webnotes.logger.error("setup_control.is_setup_okay: Passed Values:" + args['account_name'] + " " + args['user'] + " " + str(args['total_users']))
		
		if (cp_defaults==args['account_name']) and user_profile and \
		   (total_users==cint(args['total_users'])):
		   return 'True'
		