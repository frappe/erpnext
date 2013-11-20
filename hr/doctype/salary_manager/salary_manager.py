# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, flt
from webnotes.model import db_exists
from webnotes.model.doc import Document
from webnotes.model.bean import getlist, copy_doclist
from webnotes.model.code import get_obj
from webnotes import msgprint

	


class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		
		
	def get_emp_list(self):
		"""
			Returns list of active employees based on selected criteria 
			and for which salary structure exists		
		"""
		
		cond = self.get_filter_condition()
		cond += self.get_joining_releiving_condition()
		
		emp_list = webnotes.conn.sql("""
			select t1.name
			from `tabEmployee` t1, `tabSalary Structure` t2 
			where t1.docstatus!=2 and t2.docstatus != 2 
			and t1.name = t2.employee
		%s """% cond)

		return emp_list
		
		
	def get_filter_condition(self):
		self.check_mandatory()
		
		cond = ''
		for f in ['company', 'branch', 'department', 'designation', 'grade']:
			if self.doc.fields.get(f):
				cond += " and t1." + f + " = '" + self.doc.fields.get(f) + "'"		
		
		return cond

		
	def get_joining_releiving_condition(self):
		m = self.get_month_details(self.doc.fiscal_year, self.doc.month)
		cond = """
			and ifnull(t1.date_of_joining, '0000-00-00') <= '%(month_end_date)s' 
			and ifnull(t1.relieving_date, '2199-12-31') >= '%(month_start_date)s' 
		""" % m
		return cond
		
		
		
	def check_mandatory(self):
		for f in ['company', 'month', 'fiscal_year']:
			if not self.doc.fields[f]:
				msgprint("Please select %s to proceed" % f, raise_exception=1)
		
	
	def get_month_details(self, year, month):
		ysd = webnotes.conn.sql("select year_start_date from `tabFiscal Year` where name ='%s'"%year)[0][0]
		if ysd:
			from dateutil.relativedelta import relativedelta
			import calendar, datetime
			diff_mnt = cint(month)-cint(ysd.month)
			if diff_mnt<0:
				diff_mnt = 12-int(ysd.month)+cint(month)
			msd = ysd + relativedelta(months=diff_mnt) # month start date
			month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
			med = datetime.date(msd.year, cint(month), month_days) # month end date
			return {
				'year': msd.year, 
				'month_start_date': msd, 
				'month_end_date': med, 
				'month_days': month_days
			}

		
		
	def create_sal_slip(self):
		"""
			Creates salary slip for selected employees if already not created
		
		"""
		
		emp_list = self.get_emp_list()
		ss_list = []
		for emp in emp_list:
			if not webnotes.conn.sql("""select name from `tabSalary Slip` 
					where docstatus!= 2 and employee = %s and month = %s and fiscal_year = %s and company = %s
					""", (emp[0], self.doc.month, self.doc.fiscal_year, self.doc.company)):
				ss = webnotes.bean({
					"doctype": "Salary Slip",
					"fiscal_year": self.doc.fiscal_year,
					"employee": emp[0],
					"month": self.doc.month,
					"email_check": self.doc.send_email,
					"company": self.doc.company,
				})
				ss.insert()
				ss_list.append(ss.doc.name)
		
		return self.create_log(ss_list)
	
		
	def create_log(self, ss_list):
		log = "<b>No employee for the above selected criteria OR salary slip already created</b>"
		if ss_list:
			log = "<b>Created Salary Slip has been created: </b>\
			<br><br>%s" % '<br>'.join(ss_list)
		return log
	
				
	def get_sal_slip_list(self):
		"""
			Returns list of salary slips based on selected criteria
			which are not submitted
		"""
		cond = self.get_filter_condition()
		ss_list = webnotes.conn.sql("""
			select t1.name from `tabSalary Slip` t1 
			where t1.docstatus = 0 and month = '%s' and fiscal_year = '%s' %s
		""" % (self.doc.month, self.doc.fiscal_year, cond))
		return ss_list
			
				
	def submit_salary_slip(self):
		"""
			Submit all salary slips based on selected criteria
		"""
		ss_list = self.get_sal_slip_list()		
		not_submitted_ss = []
		for ss in ss_list:
			ss_obj = get_obj("Salary Slip",ss[0],with_children=1)
			try:
				webnotes.conn.set(ss_obj.doc, 'email_check', cint(self.doc.send_mail))
				if cint(self.doc.send_email) == 1:
					ss_obj.send_mail_funct()
					
				webnotes.conn.set(ss_obj.doc, 'docstatus', 1)
			except Exception,e:
				not_submitted_ss.append(ss[0])
				msgprint(e)
				continue
				
		return self.create_submit_log(ss_list, not_submitted_ss)
		
		
	def create_submit_log(self, all_ss, not_submitted_ss):
		log = ''
		if not all_ss:
			log = "No salary slip found to submit for the above selected criteria"
		else:
			all_ss = [d[0] for d in all_ss]
			
		submitted_ss = list(set(all_ss) - set(not_submitted_ss))		
		if submitted_ss:
			mail_sent_msg = self.doc.send_email and " (Mail has been sent to the employee)" or ""
			log = """
			<b>Submitted Salary Slips%s:</b>\
			<br><br> %s <br><br>
			""" % (mail_sent_msg, '<br>'.join(submitted_ss))
			
		if not_submitted_ss:
			log += """
				<b>Not Submitted Salary Slips: </b>\
				<br><br> %s <br><br> \
				Reason: <br>\
				May be company email id specified in employee master is not valid. <br> \
				Please mention correct email id in employee master or if you don't want to \
				send mail, uncheck 'Send Email' checkbox. <br>\
				Then try to submit Salary Slip again.
			"""% ('<br>'.join(not_submitted_ss))
		return log	
			
			
	def get_total_salary(self):
		"""
			Get total salary amount from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		tot = webnotes.conn.sql("""
			select sum(rounded_total) from `tabSalary Slip` t1 
			where t1.docstatus = 1 and month = '%s' and fiscal_year = '%s' %s
		""" % (self.doc.month, self.doc.fiscal_year, cond))
		
		return flt(tot[0][0])
	
		
	def get_acc_details(self):
		"""
			get default bank account,default salary acount from company
		"""
		amt = self.get_total_salary()
		com = webnotes.conn.sql("select default_bank_account from `tabCompany` where name = '%s'" % self.doc.company)
		
		if not com[0][0] or not com[0][1]:
			msgprint("You can set Default Bank Account in Company master.")

		ret = {
			'def_bank_acc' : com and com[0][0] or '',
			'def_sal_acc' : com and com[0][1] or '',
			'amount' : amt
		}
		return ret
