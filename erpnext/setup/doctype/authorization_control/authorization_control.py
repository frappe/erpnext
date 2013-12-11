# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, has_common, make_esc
from webnotes.model.bean import getlist
from webnotes import session, msgprint
from setup.utils import get_company_currency

	
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl


	# Get Names of all Approving Users and Roles
	# -------------------------------------------
	def get_appr_user_role(self, det, doctype_name, total, based_on, condition, item, company):
		amt_list, appr_users, appr_roles = [], [], []
		users, roles = '',''
		if det:
			for x in det:
				amt_list.append(flt(x[0]))
			max_amount = max(amt_list)
			
			app_dtl = webnotes.conn.sql("select approving_user, approving_role from `tabAuthorization Rule` where transaction = %s and (value = %s or value > %s) and docstatus != 2 and based_on = %s and company = %s %s" % ('%s', '%s', '%s', '%s', '%s', condition), (doctype_name, flt(max_amount), total, based_on, company))
			
			if not app_dtl:
				app_dtl = webnotes.conn.sql("select approving_user, approving_role from `tabAuthorization Rule` where transaction = %s and (value = %s or value > %s) and docstatus != 2 and based_on = %s and ifnull(company,'') = '' %s" % ('%s', '%s', '%s', '%s', condition), (doctype_name, flt(max_amount), total, based_on)) 
			for d in app_dtl:
				if(d[0]): appr_users.append(d[0])
				if(d[1]): appr_roles.append(d[1])
			
			if not has_common(appr_roles, webnotes.user.get_roles()) and not has_common(appr_users, [session['user']]):
				msg, add_msg = '',''
				if max_amount:
					dcc = get_company_currency(self.doc.company)
					if based_on == 'Grand Total': msg = "since Grand Total exceeds %s. %s" % (dcc, flt(max_amount))
					elif based_on == 'Itemwise Discount': msg = "since Discount exceeds %s for Item Code : %s" % (cstr(max_amount)+'%', item)
					elif based_on == 'Average Discount' or based_on == 'Customerwise Discount': msg = "since Discount exceeds %s" % (cstr(max_amount)+'%')
				
				if appr_users: add_msg = "Users : "+cstr(appr_users)
				if appr_roles: add_msg = "Roles : "+cstr(appr_roles)
				if appr_users and appr_roles: add_msg = "Users : "+cstr(appr_users)+" or "+"Roles : "+cstr(appr_roles)
				msgprint("You are not authorize to submit this %s %s. Please send for approval to %s" % (doctype_name, msg, add_msg))
				raise Exception


	# Check if authorization rule is set specific to user
	# ----------------------------------------------------
	def validate_auth_rule(self, doctype_name, total, based_on, cond, company, item = ''):
		chk = 1
		add_cond1,add_cond2	= '',''
		if based_on == 'Itemwise Discount':
			add_cond1 += " and master_name = '"+cstr(item)+"'"
			itemwise_exists = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction = %s and value <= %s and based_on = %s and company = %s and docstatus != 2 %s %s" % ('%s', '%s', '%s', '%s', cond, add_cond1), (doctype_name, total, based_on, company))
			if not itemwise_exists:
				itemwise_exists = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction = %s and value <= %s and based_on = %s and ifnull(company,'') = '' and docstatus != 2 %s %s" % ('%s', '%s', '%s', cond, add_cond1), (doctype_name, total, based_on))
			if itemwise_exists:
				self.get_appr_user_role(itemwise_exists, doctype_name, total, based_on, cond+add_cond1, item,company)
				chk = 0
		if chk == 1:
			if based_on == 'Itemwise Discount': add_cond2 += " and ifnull(master_name,'') = ''"
			appr = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction = %s and value <= %s and based_on = %s and company = %s and docstatus != 2 %s %s" % ('%s', '%s', '%s', '%s', cond, add_cond2), (doctype_name, total, based_on, company))
			
			if not appr:
				appr = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction = %s and value <= %s and based_on = %s and ifnull(company,'') = '' and docstatus != 2 %s %s"% ('%s', '%s', '%s', cond, add_cond2), (doctype_name, total, based_on))
			self.get_appr_user_role(appr, doctype_name, total, based_on, cond+add_cond2, item, company)
			
			
	# Bifurcate Authorization based on type
	# --------------------------------------
	def bifurcate_based_on_type(self, doctype_name, total, av_dis, based_on, doc_obj, val, company):
		add_cond = ''
		auth_value = av_dis
		if val == 1: add_cond += " and system_user = '"+session['user']+"'"
		elif val == 2: add_cond += " and system_role IN %s" % ("('"+"','".join(webnotes.user.get_roles())+"')")
		else: add_cond += " and ifnull(system_user,'') = '' and ifnull(system_role,'') = ''"
		if based_on == 'Grand Total': auth_value = total
		elif based_on == 'Customerwise Discount':
			if doc_obj:
				if doc_obj.doc.doctype == 'Sales Invoice': customer = doc_obj.doc.customer
				else: customer = doc_obj.doc.customer_name
				add_cond = " and master_name = '"+make_esc("'")(cstr(customer))+"'"
		if based_on == 'Itemwise Discount':
			if doc_obj:
				for t in getlist(doc_obj.doclist, doc_obj.fname):
					self.validate_auth_rule(doctype_name, t.adj_rate, based_on, add_cond, company,t.item_code )
		else:
			self.validate_auth_rule(doctype_name, auth_value, based_on, add_cond, company)


	# Check Approving Authority for transactions other than expense voucher and Appraisal
	# -------------------------
	def validate_approving_authority(self, doctype_name,company, total, doc_obj = ''):
		av_dis = 0
		if doc_obj:
			ref_rate, basic_rate = 0, 0
			for d in getlist(doc_obj.doclist, doc_obj.fname):
				if d.base_ref_rate and d.basic_rate:
					ref_rate += flt(d.base_ref_rate)
					basic_rate += flt(d.basic_rate)
			if ref_rate: av_dis = 100 - flt(basic_rate * 100 / ref_rate)

		final_based_on = ['Grand Total','Average Discount','Customerwise Discount','Itemwise Discount']
		# Individual User
		# ================
		# Check for authorization set for individual user
	 
		based_on = [x[0] for x in webnotes.conn.sql("select distinct based_on from `tabAuthorization Rule` where transaction = %s and system_user = %s and (company = %s or ifnull(company,'')='') and docstatus != 2", (doctype_name, session['user'], company))]

		for d in based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, d, doc_obj, 1, company)
		
		# Remove user specific rules from global authorization rules
		for r in based_on:
			if r in final_based_on and r != 'Itemwise Discount': final_based_on.remove(r)
		
		# Specific Role
		# ===============
		# Check for authorization set on particular roles
		based_on = [x[0] for x in webnotes.conn.sql("""select based_on 
			from `tabAuthorization Rule` 
			where transaction = %s and system_role IN (%s) and based_on IN (%s) 
			and (company = %s or ifnull(company,'')='') 
			and docstatus != 2
		""" % ('%s', "'"+"','".join(webnotes.user.get_roles())+"'", "'"+"','".join(final_based_on)+"'", '%s'), (doctype_name, company))]
		
		for d in based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, d, doc_obj, 2, company)
		
		# Remove role specific rules from global authorization rules
		for r in based_on:
			if r in final_based_on and r != 'Itemwise Discount': final_based_on.remove(r)
			
		# Global Rule
		# =============
		# Check for global authorization
		for g in final_based_on:
			self.bifurcate_based_on_type(doctype_name, total, av_dis, g, doc_obj, 0, company)
	
	#========================================================================================================================
	# payroll related check
	def get_value_based_rule(self,doctype_name,employee,total_claimed_amount,company):
		val_lst =[]
		val = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction=%s and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and ifnull(value,0)< %s and company = %s and docstatus!=2",(doctype_name,employee,employee,total_claimed_amount,company))
		if not val:
			val = webnotes.conn.sql("select value from `tabAuthorization Rule` where transaction=%s and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and ifnull(value,0)< %s and ifnull(company,'') = '' and docstatus!=2",(doctype_name, employee, employee, total_claimed_amount))

		if val:
			val_lst = [y[0] for y in val]
		else:
			val_lst.append(0)
	
		max_val = max(val_lst)
		rule = webnotes.conn.sql("select name, to_emp, to_designation, approving_role, approving_user from `tabAuthorization Rule` where transaction=%s and company = %s and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and ifnull(value,0)= %s and docstatus!=2",(doctype_name,company,employee,employee,flt(max_val)), as_dict=1)
		if not rule:
			rule = webnotes.conn.sql("select name, to_emp, to_designation, approving_role, approving_user from `tabAuthorization Rule` where transaction=%s and ifnull(company,'') = '' and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and ifnull(value,0)= %s and docstatus!=2",(doctype_name,employee,employee,flt(max_val)), as_dict=1)

		return rule
	
	#---------------------------------------------------------------------------------------------------------------------
	# related to payroll module only
	def get_approver_name(self, doctype_name, total, doc_obj=''):
		app_user=[]
		app_specific_user =[]
		rule ={}
		
		if doc_obj:
			if doctype_name == 'Expense Claim':
				rule = self.get_value_based_rule(doctype_name,doc_obj.doc.employee,doc_obj.doc.total_claimed_amount, doc_obj.doc.company)
			elif doctype_name == 'Appraisal':
				rule = webnotes.conn.sql("select name, to_emp, to_designation, approving_role, approving_user from `tabAuthorization Rule` where transaction=%s and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and company = %s and docstatus!=2",(doctype_name,doc_obj.doc.employee, doc_obj.doc.employee, doc_obj.doc.company),as_dict=1)				
				if not rule:
					rule = webnotes.conn.sql("select name, to_emp, to_designation, approving_role, approving_user from `tabAuthorization Rule` where transaction=%s and (to_emp=%s or to_designation IN (select designation from `tabEmployee` where name=%s)) and ifnull(company,'') = '' and docstatus!=2",(doctype_name,doc_obj.doc.employee, doc_obj.doc.employee),as_dict=1)				
			
			if rule:
				for m in rule:
					if m['to_emp'] or m['to_designation']:
						if m['approving_user']:
							app_specific_user.append(m['approving_user'])
						elif m['approving_role']:
							user_lst = [z[0] for z in webnotes.conn.sql("select distinct t1.name from `tabProfile` t1, `tabUserRole` t2 where t2.role=%s and t2.parent=t1.name and t1.name !='Administrator' and t1.name != 'Guest' and t1.docstatus !=2",m['approving_role'])]
							for x in user_lst:
								if not x in app_user:
									app_user.append(x)
			
			if len(app_specific_user) >0:
				return app_specific_user
			else:
				return app_user
