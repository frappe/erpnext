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
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
		
	# autoname
	#=======================================================
	def autoname(self):
		self.doc.name = make_autoname('Sal Slip/' +self.doc.employee + '/.#####') 

	# Get employee details
	#=======================================================
	def get_emp_and_leave_details(self):
		# Get payment days
		if self.doc.fiscal_year and self.doc.month:
			self.get_leave_details()

		# check sal structure
		if self.doc.employee:
			struct = self.check_sal_struct()
			if struct:
				self.pull_sal_struct(struct)


	# Check sal structure
	#=======================================================
	def check_sal_struct(self):
		struct = sql("select name from `tabSalary Structure` where employee ='%s' and is_active = 'Yes' "%self.doc.employee)
		if not struct:
			msgprint("Please create Salary Structure for employee '%s'"%self.doc.employee)
			self.doc.employee = ''
		return struct and struct[0][0] or ''

	# Pull struct details
	#=======================================================
	def pull_sal_struct(self, struct):
		self.doc.clear_table(self.doclist, 'earning_details')
		self.doc.clear_table(self.doclist, 'deduction_details')

		get_obj('DocType Mapper', 'Salary Structure-Salary Slip').dt_map('Salary Structure', 'Salary Slip', struct, self.doc, self.doclist, "[['Salary Structure', 'Salary Slip'],['Earning Detail', 'SS Earning Detail'],['Deduction Detail','SS Deduction Detail']]")

		basic_info = sql("select bank_name, bank_ac_no, esic_card_no, pf_number from `tabEmployee` where name ='%s'" % self.doc.employee)
		self.doc.bank_name = basic_info[0][0]
		self.doc.bank_account_no = basic_info[0][1]
		self.doc.esic_no = basic_info[0][2]
		self.doc.pf_no = basic_info[0][3]

	# Get leave details
	#=======================================================
	def get_leave_details(self):
		m = self.get_month_details()		
		lwp = self.calculate_lwp(m)
		self.doc.total_days_in_month = m[3]
		self.doc.leave_without_pay = lwp
		self.doc.payment_days = flt(m[3]) - flt(lwp)

	# Get month details
	#=======================================================
	def get_month_details(self):
		ysd = sql("select year_start_date from `tabFiscal Year` where name ='%s'"%self.doc.fiscal_year)[0][0]
		if ysd:
			from dateutil.relativedelta import relativedelta
			import calendar, datetime
			mnt = int(self.doc.month)
			diff_mnt = int(mnt)-int(ysd.month)
			if diff_mnt<0:
				diff_mnt = 12-int(ysd.month)+int(mnt)
			msd = ysd + relativedelta(months=diff_mnt) # month start date
			month_days = cint(calendar.monthrange(cint(msd.year) ,cint(self.doc.month))[1]) # days in month
			med = datetime.date(msd.year, cint(self.doc.month), month_days) # month end date
			return msd.year, msd, med, month_days

	# Calculate LWP
	#=======================================================
	def calculate_lwp(self, m):
		holidays = sql("select t1.holiday_date from `tabHoliday List Detail` t1, tabEmployee t2 where t1.parent = t2.holiday_list and t2.name = '%s' and t1.holiday_date between '%s' and '%s'" % (self.doc.employee, m[1], m[2]))
		if not holidays:
			holidays = sql("select t1.holiday_date from `tabHoliday List Detail` t1, `tabHoliday List` t2 where t1.parent = t2.name and ifnull(t2.is_default, 0) = 1 and t2.fiscal_year = '%s'" % self.doc.fiscal_year)
		holidays = [cstr(i[0]) for i in holidays]
		lwp = 0
		for d in range(m[3]):
			dt = add_days(cstr(m[1]), d)
			if dt not in holidays:
				leave = sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2 
					where t2.name = t1.leave_type 
					and ifnull(t2.is_lwp, 0) = 1 
					and t1.docstatus = 1 
					and t1.employee = '%s' 
					and '%s' between from_date and to_date
				"""%(self.doc.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and lwp + 0.5 or lwp + 1
		return lwp
					
	# Check existing
	#=======================================================
	def check_existing(self):
		ret_exist = sql("select name from `tabSalary Slip` where month = '%s' and fiscal_year = '%s' and docstatus != 2 and employee = '%s' and name !='%s'" % (self.doc.month,self.doc.fiscal_year,self.doc.employee,self.doc.name))
		if ret_exist:
			msgprint("Salary Slip of employee '%s' already created for this month" % self.doc.employee)
			self.doc.employee = ''
			raise Exception

	# Validate
	#=======================================================
	def validate(self):
		self.check_existing()
		dcc = TransactionBase().get_company_currency(self.doc.company)
		self.doc.total_in_words	= get_obj('Sales Common').get_total_in_words(dcc, self.doc.rounded_total)
		
	# ON SUBMIT
	#=======================================================
	def on_submit(self):
		if(self.doc.email_check == 1):			
			self.send_mail_funct()

	# Send mail
	#=======================================================
	def send_mail_funct(self):	 
		emailid_ret=sql("select company_email from `tabEmployee` where name = '%s'"%self.doc.employee)
		if emailid_ret:
			receiver = cstr(emailid_ret[0][0]) 
			subj = 'Salary Slip ' + cstr(self.doc.month) +' '+cstr(self.doc.year)
			earn_ret=sql("select e_type,e_amount from `tabSS Earning Detail` where parent = '%s'"%self.doc.name)
			ded_ret=sql("select d_type,d_amount from `tabSS Deduction Detail` where parent = '%s'"%self.doc.name)
		 
			earn_table = ''
			ded_table = ''
			if earn_ret:
			
				earn_table += "<table cellspacing= '5' cellpadding='5' >"
				
				for e in earn_ret:
					if not e[1]:
						earn_table +='<tr><td>%s</td><td>0.00</td></tr>'%(cstr(e[0]))
					else:
						earn_table +='<tr><td>%s</td><td>%s</td></tr>'%(cstr(e[0]),cstr(e[1]))
				earn_table += '</table>'
			
			if ded_ret:
			
				ded_table += "<table cellspacing= '5' cellpadding='5' >"
				
				for d in ded_ret:
					if not d[1]:
						ded_table +='<tr><td>%s</td><td>0.00</td></tr>'%(cstr(d[0]))
					else:
						ded_table +='<tr><td>%s</td><td>%s</td></tr>'%(cstr(d[0]),cstr(d[1]))
				ded_table += '</table>'
			
			letter_head = sql("select value from `tabSingles` where field = 'letter_head' and doctype = 'Control Panel'")
			
			if not letter_head:
				letter_head = ''
			
			msg = ''' %s <br>
			<table cellspacing= "5" cellpadding="5" >
			<tr>
				<td colspan = 4><h4>Salary Slip</h4></td>
			</tr>
			<tr>
				<td colspan = 2><b>Employee Code : %s</b></td>
				<td colspan = 2><b>Employee Name : %s</b></td>
			</tr>
			<tr>
				<td>Month : %s</td>
				<td>Year : %s</td>
				<td colspan = 2>Fiscal Year : %s</td>
			</tr>
			<tr>
				<td>Department : %s</td>
				<td>Branch : %s</td>
				<td colspan = 2>Designation : %s</td>
				
			</tr>
			<tr>
				<td>Grade : %s</td>
				<td>Bank Account No. : %s</td>
				<td colspan = 2>Bank Name : %s</td>
				
			</tr>
			<tr>
				<td>PF No. : %s</td>
				<td>ESIC No. : %s</td>
				<td colspan = 2>Arrear Amount : <b>%s</b></td>
			</tr>
			<tr>
				<td>Total days in month : %s</td>
				<td>Leave Without Pay : %s</td>
				<td colspan = 2>Payment days : %s</td>
				
			</tr>
			<br><br>
			<tr>
				<td colspan = 2><b>Earning</b></td>
				<td colspan = 2><b>Deduction</b></td>
			</tr>
			<tr>
				<td colspan = 2>%s</td>
				<td colspan = 2>%s</td>
			</tr>
			<br>
			<tr>
				<td colspan = 2><b>Gross Pay :</b> %s</td>
				<td colspan = 2><b>Total Deduction :</b> %s</td>
			</tr>
			<tr>
				<td><b>Net Pay : %s</b></td>
				<td colspan = 3><b>Net Pay (in words) : %s</b></td>
			</tr>
			</table>'''%(cstr(letter_head[0][0]),cstr(self.doc.employee),self.doc.employee_name,cstr(self.doc.month),cstr(self.doc.year),cstr(self.doc.fiscal_year),self.doc.department,self.doc.branch,self.doc.designation,self.doc.grade,cstr(self.doc.bank_account_no),self.doc.bank_name,cstr(self.doc.pf_no),cstr(self.doc.esic_no),cstr(self.doc.arrear_amount),cstr(self.doc.total_days_in_month),cstr(self.doc.leave_without_pay),cstr(self.doc.payment_days),earn_table,ded_table,cstr(self.doc.gross_pay),cstr(self.doc.total_deduction),cstr(self.doc.net_pay),cstr(self.doc.net_pay_in_words))
			sendmail([receiver], sender='automail@webnotestech.com', subject=subj, parts=[['text/plain', msg]])
		else:
			msgprint("Company Email ID not found.")
