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
  #init function
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist
 
  #autoname function
  #---------------------------------------------------------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.employee + '/.SST' + '/.#####')
  
  #get employee details
  #---------------------------------------------------------
  def get_employee_details(self):
    ret = {}
    det = sql("select employee_name, branch, designation, department, grade from `tabEmployee` where name = '%s'" %self.doc.employee)
    if det:
      ret = {
        'employee_name'  : cstr(det[0][0]),
        'branch'         : cstr(det[0][1]),
        'designation'    : cstr(det[0][2]),
        'department'     : cstr(det[0][3]),
        'grade'          : cstr(det[0][4]),
        'backup_employee': cstr(self.doc.employee)
      }
    return ret
    

  # Set Salary structure field values
  #---------------------------------------------------------
  def get_ss_values(self,employee):
    basic_info = sql("select bank_name, bank_ac_no, esic_card_no, pf_number from `tabEmployee` where name ='%s'" % employee)
    ret = {'bank_name'   : basic_info and basic_info[0][0] or '',
            'bank_ac_no'  : basic_info and basic_info[0][1] or '',
            'esic_no'     : basic_info and basic_info[0][2] or '',
            'pf_no'       : basic_info and basic_info[0][3] or ''}
    return ret
   
  # Make earning and deduction table    
  #---------------------------------------------------------
  def make_table(self, doct_name, tab_fname, tab_name):
    list1 = sql("select name from `tab%s` where docstatus != 2" % doct_name)
    for li in list1:
      child = addchild(self.doc, tab_fname, tab_name, 1, self.doclist)
      if(tab_fname == 'earning_details'):
        child.e_type = cstr(li[0])
        child.modified_value = 0
      elif(tab_fname == 'deduction_details'):
        child.d_type = cstr(li[0])
        child.d_modified_amt = 0
    
  # add earning & deduction types to table 
  #---------------------------------------------------------   
  def make_earn_ded_table(self):           
    #Earning List
    self.make_table('Earning Type','earning_details','Earning Detail')
    
    #Deduction List
    self.make_table('Deduction Type','deduction_details', 'Deduction Detail')
    

  # Check if another active ss exists
  #---------------------------------------------------------
  def check_existing(self):
    ret = sql("select name from `tabSalary Structure` where is_active = 'Yes' and employee = '%s' and name!='%s'" %(self.doc.employee,self.doc.name))
    if ret and self.doc.is_active=='Yes':
      msgprint("Another Salary Structure '%s' is active for employee '%s'. Please make its status 'Inactive' to proceed."%(cstr(ret), self.doc.employee))
      raise Exception

  # Validate net pay
  #---------------------------------------------------------
  def validate_net_pay(self):
    if flt(self.doc.net_pay) < 0:
      msgprint("Net pay can not be negative")
      raise Exception
    elif flt(self.doc.net_pay) > flt(self.doc.ctc):
      msgprint("Net pay can not be greater than CTC")
      raise Exception      

  # Validate
  #---------------------------------------------------------
  def validate(self):   
    self.check_existing()
    self.validate_net_pay()

