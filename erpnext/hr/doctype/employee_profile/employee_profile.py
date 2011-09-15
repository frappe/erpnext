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


  #=============================================================
  def autoname(self):
    self.doc.name = make_autoname('EMP-'+self.doc.employee)

  #=============================================================
  def validate(self):
    if self.doc.personal_email:
      if not validate_email_add(self.doc.personal_email):
        msgprint("Please enter valid Personal Email")
        raise Exception
    ret = sql("select name from `tabEmployee Profile` where employee = '%s' and name !='%s'"%(self.doc.employee,self.doc.name))
    if ret:
      msgprint("Employee Profile is already created for Employee : '%s'"%self.doc.employee)
      raise Exception

  #=============================================================
  def get_doj(self):
    ret_doj = sql("select employee_name,date_of_joining from `tabEmployee` where name = '%s'"%self.doc.employee)
    if ret_doj:
      set(self.doc, 'employee_name', cstr(ret_doj[0][0]))
      set(self.doc,'date_of_joining', ret_doj[0][1].strftime('%Y-%m-%d'))

  #=============================================================
  #calculate total experience in company - total year and month
  def cal_tot_exp(self):
    if not self.doc.date_of_joining:
      self.get_doj()
    
      import datetime
      today  = nowdate()
    
      diff = (getdate(today) - getdate(self.doc.date_of_joining)).days
      diff1 = cint(diff)/365
      a = cint(diff)%365
      diff2 = cint(a)/30
      if(cint(diff1)<0):
        set(self.doc,'year', 0)
      else:
        set(self.doc,'year', cint(diff1))
      if(cint(diff1)<0):
        set(self.doc,'months', 0)
      else:
        set(self.doc,'months', cint(diff2)) 

  #=============================================================
  def check_state(self,country):
    return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " %country)])
