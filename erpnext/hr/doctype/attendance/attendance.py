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
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
    
  #autoname function
  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')
  
  #get employee name based on employee id selected 
  def get_emp_name(self):
    emp_nm = sql("select employee_name from `tabEmployee` where name=%s", self.doc.employee)

    #this is done because sometimes user entered wrong employee name while uploading employee attendance
    set(self.doc, 'employee_name', emp_nm and emp_nm[0][0] or '')

    ret = { 'employee_name' : emp_nm and emp_nm[0][0] or ''}
    return ret
  
  #validation for duplicate record
  def validate_duplicate_record(self):   
    res = sql("select name from `tabAttendance` where employee = '%s' and att_date = '%s' and not name = '%s' and docstatus = 1"%(self.doc.employee,self.doc.att_date, self.doc.name))
    if res:
      msgprint("Employee's attendance already marked.")
      raise Exception
      
  #validation - leave_type is mandatory for status absent/ half day else not required to entered.
  def validate_status(self):
    if self.doc.status == 'Present' and self.doc.leave_type:
      msgprint("You can not enter leave type for attendance status 'Present'")
      raise Exception

    elif (self.doc.status == 'Absent' or self.doc.status == 'Half Day') and not self.doc.leave_type:
      msgprint("Please enter leave type for attendance status 'Absent'")
      raise Exception
  
  #check for already record present in leave transaction for same date
  def check_leave_record(self):
    if self.doc.status == 'Present':
      chk = sql("select name from `tabLeave Transaction` where employee=%s and (from_date <= %s and to_date >= %s) and status = 'Submitted' and leave_transaction_type = 'Deduction' and docstatus!=2", (self.doc.employee, self.doc.att_date, self.doc.att_date))
      if chk:
        msgprint("Leave Application created for employee "+self.doc.employee+" whom you are trying to mark as 'Present' ")
        raise Exception
  
  #For absent/ half day record - check for leave balances of the employees 
  def validate_leave_type(self):
    if not self.doc.status =='Present' and self.doc.leave_type not in ('Leave Without Pay','Compensatory Off'):
      #check for leave allocated to employee from leave transaction
      ret = sql("select name from `tabLeave Transaction` where employee = '%s' and leave_type = '%s' and leave_transaction_type = 'Allocation' and fiscal_year = '%s'"%(self.doc.employee,self.doc.leave_type,self.doc.fiscal_year))   
      
      #if leave allocation is present then calculate leave balance i.e. sum(allocation) - sum(deduction) 
      if ret:
        q1 = 'SUM(CASE WHEN leave_transaction_type = "Allocation" THEN total_leave ELSE 0 END)-SUM(CASE WHEN leave_transaction_type = "Deduction" THEN total_leave ELSE 0 END)'
        q2 = "select %s from `tabLeave Transaction` where employee = '%s' and leave_type = '%s' and fiscal_year = '%s' and docstatus = 1"
        
        res = sql(q2%(q1,self.doc.employee,self.doc.leave_type,self.doc.fiscal_year))
       
        if res:
          if self.doc.status == 'Absent' and flt(res[0][0]) < 1:
            msgprint("%s balances are insufficient to cover a day absence, please select other leave type."%self.doc.leave_type)
            raise Exception
          if self.doc.status == 'Half Day' and flt(res[0][0]) < 0.5:
            msgprint("%s balances are insufficient to cover a half day absence, please select other leave type."%self.doc.leave_type)
            raise Exception

      else:
        msgprint("Leave Allocation for employee %s not done.\n You can allocate leaves from HR -> Leave Transaction OR HR -> Leave Control Panel."%self.doc.employee)
        raise Exception
         
  def validate_fiscal_year(self):
    fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"% self.doc.fiscal_year)
    ysd=fy and fy[0][0] or ""
    yed=add_days(str(ysd),365)
    if str(self.doc.att_date) < str(ysd) or str(self.doc.att_date) > str(yed):
      msgprint("'%s' Not Within The Fiscal Year selected"%(self.doc.att_date))
      raise Exception
  
  def validate_att_date(self):
    import datetime
    if getdate(self.doc.att_date)>getdate(datetime.datetime.now().date().strftime('%Y-%m-%d')):
      msgprint("Attendance can not be marked for future dates")
      raise Exception

  # Validate employee
  #-------------------
  def validate_employee(self):
    emp = sql("select name, status from `tabEmployee` where name = '%s'" % self.doc.employee)
    if not emp:
      msgprint("Employee: %s does not exists in the system" % self.doc.employee, raise_exception=1)
    elif emp[0][1] != 'Active':
      msgprint("Employee: %s is not Active" % self.doc.employee, raise_exception=1)
      
  # validate...
  def validate(self):
    self.validate_fiscal_year()
    self.validate_att_date()
    #self.validate_leave_type()
    self.validate_duplicate_record()
    #self.validate_status()
    self.check_leave_record()
    
  def on_update(self):
    #self.validate()
    
    #this is done because sometimes user entered wrong employee name while uploading employee attendance
    x=self.get_emp_name()

  def on_submit(self):
    #this is done because while uploading attendance chnage docstatus to 1 i.e. submit
    set(self.doc,'docstatus',1)
    pass
