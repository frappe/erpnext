 # ERPNext - web based ERP (http://erpnext.com)
 # Copyright (C) 2012 Web Notes Technologies Pvt Ltd
 
 # This program is free software: you can redistribute it and/or modify
 # it under the terms of the GNU General Public License as published by
 # the Free Software Foundation, either version 3 of the License, or
 # (at your option) any later version.

 # This program is distributed in the hope that it will be useful,
 # but WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 # GNU General Public License for more details.
 
 # You should have received a copy of the GNU General Public License
 # along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

def get_filters_cond(doctype, filters, conditions):
	if filters:
		if isinstance(filters, dict):
			filters = filters.items()
			flt = []
			for f in filters:
				if f[1][0] == '!':
					flt.append([doctype, f[0], '!=', f[1][1:]])
				else:
					flt.append([doctype, f[0], '=', f[1]])
		
		from webnotes.widgets.reportview import build_filter_conditions
		build_filter_conditions(flt, conditions)
		cond = ' and ' + ' and '.join(conditions)	
	else:
		cond = ''
	return cond

def get_match_cond(doctype, searchfield = 'name'):
	meta = webnotes.get_doctype(doctype)
	from webnotes.widgets.search import get_std_fields_list
	fields = get_std_fields_list(meta, searchfield)

	from webnotes.widgets.reportview import build_match_conditions
	cond = build_match_conditions(doctype, fields)

	if cond:
		cond = ' and ' + cond
	else:
		cond = ''
	return cond

 # searches for enabled profiles
def profile_query(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, concat_ws(' ', first_name, middle_name, last_name) 
		from `tabProfile` 
		where ifnull(enabled, 0)=1 
			and docstatus < 2 
			and name not in ('Administrator', 'Guest') 
			and (%(key)s like "%(txt)s" 
				or concat_ws(' ', first_name, middle_name, last_name) like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when concat_ws(' ', first_name, middle_name, last_name) like "%(txt)s" 
				then 0 else 1 end, 
			name asc 
		limit %(start)s, %(page_len)s""" % {'key': searchfield, 'txt': "%%%s%%" % txt,  
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

 # searches for active employees
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, employee_name from `tabEmployee` 
		where status = 'Active' 
			and docstatus < 2 
			and (%(key)s like "%(txt)s" 
				or employee_name like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when employee_name like "%(txt)s" then 0 else 1 end, 
			name 
		limit %(start)s, %(page_len)s""" % {'key': searchfield, 'txt': "%%%s%%" % txt,  
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

 # searches for leads which are not converted
def lead_query(doctype, txt, searchfield, start, page_len, filters): 
	return webnotes.conn.sql("""select name, lead_name, company_name from `tabLead`
		where docstatus < 2 
			and ifnull(status, '') != 'Converted' 
			and (%(key)s like "%(txt)s" 
				or lead_name like "%(txt)s" 
				or company_name like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when lead_name like "%(txt)s" then 0 else 1 end, 
			case when company_name like "%(txt)s" then 0 else 1 end, 
			lead_name asc 
		limit %(start)s, %(page_len)s""" % {'key': searchfield, 'txt': "%%%s%%" % txt,  
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

 # searches for customer
def customer_query(doctype, txt, searchfield, start, page_len, filters):
	cust_master_name = webnotes.defaults.get_user_default("cust_master_name")

	if cust_master_name == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]

	fields = ", ".join(fields) 

	return webnotes.conn.sql("""select %(field)s from `tabCustomer` 
		where docstatus < 2 
			and (%(key)s like "%(txt)s" 
				or customer_name like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when customer_name like "%(txt)s" then 0 else 1 end, 
			name, customer_name 
		limit %(start)s, %(page_len)s""" % {'field': fields,'key': searchfield, 
		'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype, searchfield), 
		'start': start, 'page_len': page_len})

# searches for supplier
def supplier_query(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = webnotes.defaults.get_user_default("supp_master_name")
	if supp_master_name == "Supplier Name":  
		fields = ["name", "supplier_type"]
	else: 
		fields = ["name", "supplier_name", "supplier_type"]
	fields = ", ".join(fields) 

	return webnotes.conn.sql("""select %(field)s from `tabSupplier` 
		where docstatus < 2 
			and (%(key)s like "%(txt)s" 
				or supplier_name like "%(txt)s") 
			%(mcond)s
		order by 
			case when name like "%(txt)s" then 0 else 1 end, 
			case when supplier_name like "%(txt)s" then 0 else 1 end, 
			name, supplier_name 
		limit %(start)s, %(page_len)s """ % {'field': fields,'key': searchfield, 
		'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype, searchfield), 'start': start, 
		'page_len': page_len})

def item_std(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select tabItem.name, 
		if(length(tabItem.item_name) > 40, 
			concat(substr(tabItem.item_name, 1, 40), "..."), item_name) as item_name, 
		if(length(tabItem.description) > 40, 
			concat(substr(tabItem.description, 1, 40), "..."), description) as decription 
		FROM tabItem 
		WHERE tabItem.docstatus!=2 
			and tabItem.%(key)s LIKE "%(txt)s" 
			%(mcond)s 
		limit %(start)s, %(page_len)s """ % {'key': searchfield, 'txt': "%%%s%%" % txt, 
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 
		'page_len': page_len})

def account_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	if not filters:
		filters = {}
	if not filters.group_or_ledger:
		filters.group_or_ledger = "Ledger"
	
	return webnotes.conn.sql("""
		select tabAccount.name, tabAccount.parent_account, tabAccount.debit_or_credit 
		from tabAccount 
		where tabAccount.docstatus!=2 
			and 
			and tabAccount.%(key)s LIKE "%(txt)s" 
		 	%(fcond)s %(mcond)s 
		limit %(start)s, %(page_len)s""" % {'key': searchfield, 
		'txt': "%%%s%%" % txt, 'fcond': get_filters_cond(doctype, filters, conditions), 
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})
		
def tax_account_query(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name, parent_account, debit_or_credit 
		from tabAccount 
		where tabAccount.docstatus!=2 
			and (account_type in (%s) or 
				(ifnull(is_pl_account, 'No') = 'Yes' and debit_or_credit = %s) )
			and group_or_ledger = 'Ledger'
			and company = %s
			and `%s` LIKE %s
		limit %s, %s""" % 
		(", ".join(['%s']*len(filters.get("account_type"))), 
			"%s", "%s", searchfield, "%s", "%s", "%s"), 
		tuple(filters.get("account_type") + [filters.get("debit_or_credit"), 
			filters.get("company"), "%%%s%%" % txt, start, page_len]))

def item_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	return webnotes.conn.sql("""select tabItem.name, 
		if(length(tabItem.item_name) > 40, 
			concat(substr(tabItem.item_name, 1, 40), "..."), item_name) as item_name, 
		if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as decription 
		from tabItem 
		where tabItem.docstatus!=2 
			and (ifnull(`tabItem`.`end_of_life`,"") in ("", "0000-00-00") 
				or `tabItem`.`end_of_life` > NOW()) 
			and (tabItem.%(key)s LIKE "%(txt)s" 
				or tabItem.item_name LIKE "%(txt)s")  
			%(fcond)s %(mcond)s 
		limit %(start)s,%(page_len)s """ %  {'key': searchfield, 'txt': "%%%s%%" % txt, 
		'fcond': get_filters_cond(doctype, filters, conditions), 
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

def bom(doctype, txt, searchfield, start, page_len, filters):
	conditions = []	

	return webnotes.conn.sql("""select tabBOM.name, tabBOM.item 
		from tabBOM 
		where tabBOM.docstatus=1 
			and tabBOM.is_active=1 
			and tabBOM.%(key)s like "%(txt)s"  
			%(fcond)s  %(mcond)s  
		limit %(start)s, %(page_len)s """ %  {'key': searchfield, 'txt': "%%%s%%" % txt, 
		'fcond': get_filters_cond(doctype, filters, conditions), 
		'mcond':get_match_cond(doctype, searchfield), 'start': start, 'page_len': page_len})

def get_project_name(doctype, txt, searchfield, start, page_len, filters):
	cond = ''
	if filters['customer']:
		cond = '(`tabProject`.customer = "' + filters['customer'] + '" or ifnull(`tabProject`.customer,"")="") and'
	
	return webnotes.conn.sql("""select `tabProject`.name from `tabProject` 
		where `tabProject`.status not in ("Completed", "Cancelled") 
			and %(cond)s `tabProject`.name like "%(txt)s" %(mcond)s 
		order by `tabProject`.name asc 
		limit %(start)s, %(page_len)s """ % {'cond': cond,'txt': "%%%s%%" % txt, 
		'mcond':get_match_cond(doctype, searchfield),'start': start, 'page_len': page_len})
		
def get_price_list_currency(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select ref_currency from `tabItem Price` 
		where price_list_name = %s and buying_or_selling = %s
		and `%s` like %s order by ref_currency asc limit %s, %s""" %
		("%s", "%s", searchfield, "%s", "%s", "%s"), 
		(filters["price_list_name"], filters['buying_or_selling'], "%%%s%%" % txt, 
			start, page_len))