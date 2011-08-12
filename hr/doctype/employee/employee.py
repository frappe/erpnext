import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists

# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist

  # Autoname
  #========================================================================================================
  def autoname(self):
    ret = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = 'emp_created_by'")
    if not ret:
      msgprint("To Save Employee, please go to Setup -->Global Defaults. Click on HR and select 'Employee Records to be created by'.")
      raise Exception 
    else:
      if ret[0][0]=='Naming Series':
        self.doc.name = make_autoname(self.doc.naming_series + '.####')
      elif ret[0][0]=='Employee Number':
        self.doc.name = make_autoname(self.doc.employee_number)
        
  # Get retirement date
  #========================================================================================================
  def get_retirement_date(self):    
    import datetime
    ret = {}
    if self.doc.date_of_birth:
      dt = getdate(self.doc.date_of_birth) + datetime.timedelta(21915)
      ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
    return ret

  # check if salary structure exists
  #========================================================================================================
  def check_sal_structure(self, nm):
    ret_sal_struct=sql("select name from `tabSalary Structure` where employee='%s' and is_active = 'Yes'"%nm)
    return ret_sal_struct and ret_sal_struct[0][0] or ''

  #========================================================================================================
  def validate(self):
    self.validate_date()
    self.validate_email()
    self.validate_name()
    self.validate_status()
  
  # Validate dates
  #========================================================================================================
  def validate_date(self):  
    import datetime
    if self.doc.date_of_birth and self.doc.date_of_joining and getdate(self.doc.date_of_birth) >= getdate(self.doc.date_of_joining):
      msgprint('Date of Joining must be greater than Date of Birth')
      raise Exception

    elif self.doc.scheduled_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.scheduled_confirmation_date) < getdate(self.doc.date_of_joining)):
      msgprint('Scheduled Confirmation Date must be greater than Date of Joining')
      raise Exception
    
    elif self.doc.final_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.final_confirmation_date) < getdate(self.doc.date_of_joining)):
      msgprint('Final Confirmation Date must be greater than Date of Joining')
      raise Exception
    
    elif self.doc.date_of_retirement and self.doc.date_of_joining and (getdate(self.doc.date_of_retirement) <= getdate(self.doc.date_of_joining)):
      msgprint('Date Of Retirement must be greater than Date of Joining')
      raise Exception
    
    elif self.doc.relieving_date and self.doc.date_of_joining and (getdate(self.doc.relieving_date) <= getdate(self.doc.date_of_joining)):
      msgprint('Relieving Date must be greater than Date of Joining')
      raise Exception
    
    elif self.doc.contract_end_date and self.doc.date_of_joining and (getdate(self.doc.contract_end_date)<=getdate(self.doc.date_of_joining)):
      msgprint('Contract End Date must be greater than Date of Joining')
      raise Exception
   
  # Validate email id
  #========================================================================================================
  def validate_email(self):
    if self.doc.company_email and not validate_email_add(self.doc.company_email):
      msgprint("Please enter valid Company Email")
      raise Exception
    if self.doc.personal_email and not validate_email_add(self.doc.personal_email):
      msgprint("Please enter valid Personal Email")
      raise Exception

  # Validate name
  #========================================================================================================
  def validate_name(self):  
    ret = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = 'emp_created_by'")

    if not ret:
      msgprint("To Save Employee, please go to Setup -->Global Defaults. Click on HR and select 'Employee Records to be created by'.")
      raise Exception 
    else:
      if ret[0][0]=='Naming Series' and not self.doc.naming_series:
        msgprint("Please select Naming Series.")
        raise Exception 
      elif ret[0][0]=='Employee Number' and not self.doc.employee_number:
        msgprint("Please enter Employee Number.")
        raise Exception 
        
  # Validate status
  #========================================================================================================
  def validate_status(self):
    if self.doc.status == 'Left' and not self.doc.relieving_date:
      msgprint("Please enter relieving date.")
      raise Exception
