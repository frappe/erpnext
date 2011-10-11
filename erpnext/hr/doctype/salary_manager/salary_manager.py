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
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		
		
	def get_emp_list(self):
		"""
			Returns list of active employees based on selected criteria 
			and for which salary structure exists		
		"""
		
		cond = self.get_filter_condition()
		
		emp_list = sql("""
			select t1.name
			from `tabEmployee` t1, `tabSalary Structure` t2 
			where t1.docstatus!=2 and t2.docstatus != 2 
			and ifnull(t1.status, 'Left') = 'Active' and ifnull(t2.is_active, 'No') = 'Yes' 
			and t1.name = t2.employee
		%s """% cond)

		return emp_list
		
		
	def get_filter_condition(self):
		self.check_mandatory()
		
		cond = ''
		for f in ['company', 'branch', 'department', 'designation', 'grade', 'employment_type']:
			if self.doc.fields.get(f):
				cond += " and t1." + f + " = '" + self.doc.fields.get(f) + "'"
				
		return cond
		
		
	def check_mandatory(self):
		for f in ['company', 'month', 'fiscal_year']:
			if not self.doc.fields[f]:
				msgprint("Please select %s to proceed" % f, raise_exception=1)
		
		
	def create_sal_slip(self):
		"""
			Creates salary slip for selected employees if already not created
		
		"""
		
		emp_list = self.get_emp_list()
		log = ""
		if emp_list:
			log = "<table><tr><td colspan = 2>Following Salary Slip has been created: </td></tr><tr><td><u>SAL SLIP ID</u></td><td><u>EMPLOYEE NAME</u></td></tr>"
		else:
			log = "<table><tr><td colspan = 2>No employee found for the above selected criteria</td></tr>"
			
		for emp in emp_list:
			if not sql("""select name from `tabSalary Slip` 
					where docstatus!= 2 and employee = %s and month = %s and fiscal_year = %s and company = %s
					""", (emp[0], self.doc.month, self.doc.fiscal_year, self.doc.company)):
				ss = Document('Salary Slip')
				ss.fiscal_year = self.doc.fiscal_year
				ss.employee = emp[0]
				ss.month = self.doc.month
				ss.email_check = self.doc.send_email
				ss.company = self.doc.company
				ss.save(1)
			
				ss_obj = get_obj('Salary Slip', ss.name, with_children=1)
				ss_obj.get_emp_and_leave_details()
				ss_obj.calculate_net_pay()
				ss_obj.validate()
				ss_obj.doc.save()
			
				for d in getlist(ss_obj.doclist, 'earning_details'):
					d.save()
				for d in getlist(ss_obj.doclist, 'deduction_details'):
					d.save()
					
				log += '<tr><td>' + ss.name + '</td><td>' + ss_obj.doc.employee_name + '</td></tr>'
		log += '</table>'
		return log	
				
	def get_sal_slip_list(self):
		"""
			Returns list of salary slips based on selected criteria
			which are not submitted
		"""
		cond = self.get_filter_condition()
		ss_list = sql("""
			select t1.name from `tabSalary Slip` t1 
			where t1.docstatus = 0 and month = '%s' and fiscal_year = '%s' %s
		""" % (self.doc.month, self.doc.fiscal_year, cond))
		return ss_list
			
				
	def submit_salary_slip(self):
		"""
			Submit all salary slips based on selected criteria
		"""
		ss_list = self.get_sal_slip_list()
		log = ""
		if ss_list:
			log = 	"""<table>
						<tr>
							<td colspan = 2>Following Salary Slip has been submitted: </td>
						</tr>
						<tr>
							<td><u>SAL SLIP ID</u></td>
							<td><u>EMPLOYEE NAME</u></td>
						</tr>
					"""
		else:
			log = "<table><tr><td colspan = 2>No salary slip found to submit for the above selected criteria</td></tr>"
			
		for ss in ss_list:
			ss_obj = get_obj("Salary Slip",ss[0],with_children=1)
			set(ss_obj.doc, 'docstatus', 1)
			ss_obj.on_submit()
			
			log += '<tr><td>' + ss[0] + '</td><td>' + ss_obj.doc.employee_name + '</td></tr>'
		log += '</table>'	
		return log	
			
			
	def get_total_salary(self):
		"""
			Get total salary amount from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		tot = sql("""
			select sum(rounded_total) from `tabSalary Slip` t1 
			where t1.docstatus = 1 and month = '%s' and fiscal_year = '%s' %s
		""" % (self.doc.month, self.doc.fiscal_year, cond))
		
		return flt(tot[0][0])
		
		
	def get_acc_details(self):
		"""
			get default bank account,default salary acount from company
		"""
		amt = self.get_total_salary()
		com = sql("select default_bank_account from `tabCompany` where name = '%s'" % self.doc.company)
		
		if not com[0][0] or not com[0][1]:
			msgprint("You can set Default Bank Account in Company master.")

		ret = {
			'def_bank_acc' : com and com[0][0] or '',
			'def_sal_acc' : com and com[0][1] or '',
			'amount' : amt
		}
		return ret
