# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql

# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  def get_project_details(self):
    cust = sql("select customer, customer_name from `tabProject` where name = %s", self.doc.project)
    if cust:
      ret = {'customer': cust and cust[0][0] or '', 'customer_name': cust and cust[0][1] or ''}
      return ret
  
  def get_customer_details(self):
    cust = sql("select customer_name from `tabCustomer` where name=%s", self.doc.customer)
    if cust:
      ret = {'customer_name': cust and cust[0][0] or ''}
      return ret
  
  def get_allocated_to_name(self):
    as_em = sql("select first_name, last_name from `tabProfile` where name=%s",self.doc.allocated_to)
    ret = { 'allocated_to_name' : as_em and (as_em[0][0] + ' ' + as_em[0][1]) or ''}
    return ret

  # validate
  #--------------------------------------------   


  def validate(self):
    if not self.doc.opening_date:
      msgprint("Please enter Opening Date.")
      raise Exception
    elif getdate(self.doc.opening_date) > getdate(nowdate()):
      msgprint("Opening date can not be future date")
      raise Exception
    
    if self.doc.exp_start_date and self.doc.exp_end_date and getdate(self.doc.exp_start_date) > getdate(self.doc.exp_end_date):
      msgprint("'Expected Start Date' can not be greater than 'Expected End Date'")
      raise Exception
    
    if self.doc.act_start_date and self.doc.act_end_date and getdate(self.doc.act_start_date) > getdate(self.doc.act_end_date):
      msgprint("'Actual Start Date' can not be greater than 'Actual End Date'")
      raise Exception
    
    if self.doc.opening_date and self.doc.review_date and getdate(self.doc.opening_date) > getdate(self.doc.review_date):
      msgprint("Review Date should be greater than or equal to Opening Date ")
      raise Exception
    
    if self.doc.closing_date and self.doc.review_date and getdate(self.doc.closing_date) < getdate(self.doc.review_date):
      msgprint("Closing Date should be greater than or equal to Review Date ")
      raise Exception

  # on update
  #--------------------------------------------   
  
  def on_update(self):
    pass
        
  #validate before sending for approval
  def validate_for_pending_review(self):
    if not self.doc.allocated_to:
      msgprint("Please enter allocated_to.")
      raise Exception
    self.validate_with_timesheet_dates()
  
  #validate before closing task
  def validate_for_closed(self):
    self.check_non_submitted_timesheets()
    self.get_actual_total_hrs()
  
  def check_non_submitted_timesheets(self):
    chk = sql("select t1.name from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent=t1.name and t2.task_id=%s and t1.status='Draft'", self.doc.name)
    if chk:
      chk_lst = [x[0] for x in chk]
      msgprint("Please submit timesheet(s) : "+','.join(chk_lst)+" before declaring this task as completed. As details of this task present in timesheet(s)")
      raise Exception
  
  #calculate actual total hours taken to complete task from timesheets
  def get_actual_total_hrs(self):
    import datetime
    import time
    chk = sql("select t2.act_total_hrs from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status = 'Submitted' and ifnull(t2.act_total_hrs, '')!='' order by t1.timesheet_date asc", self.doc.name)
    if chk:
      chk_lst = [x[0] for x in chk]
      actual_total = total =0
      
      for m in chk_lst:
        m1, m2=[], 0
        m1 = m.split(":")
        m2 = (datetime.timedelta(minutes=cint(m1[1]), hours=cint(m1[0]))).seconds
        total = total + m2
      
      actual_total = time.strftime("%H:%M", time.gmtime(total))
      set(self.doc, 'act_total_hrs', actual_total)
  
  # validate and fetch actual start and end date
  def validate_with_timesheet_dates(self):
    chk = sql("select t1.name, t1.timesheet_date from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status = 'Submitted' order by t1.timesheet_date asc", self.doc.name, as_dict=1)
    if chk:
      if self.doc.act_start_date:
        if chk[0]['timesheet_date'] > getdate(self.doc.act_start_date) or chk[0]['timesheet_date'] < getdate(self.doc.act_start_date):
          msgprint("Actual start date of this task is "+cstr(chk[0]['timesheet_date'])+" as per timesheet "+cstr(chk[0]['name']))
          raise Exception
      else:
        self.doc.act_start_date = chk[0]['timesheet_date']
      
      if self.doc.act_end_date:
        if chk[len(chk)-1]['timesheet_date'] < getdate(self.doc.act_end_date) or chk[len(chk)-1]['timesheet_date'] > getdate(self.doc.act_end_date):
          msgprint("Actual end date of this task is "+cstr(chk[len(chk)-1]['timesheet_date'])+" as per timesheet "+cstr(chk[len(chk)-1]['name']))
          raise Exception
      else:
        self.doc.act_end_date = chk[len(chk)-1]['timesheet_date']
  
  def set_for_review(self):
    self.check_non_submitted_timesheets()
    self.validate_for_pending_review()
    self.get_actual_total_hrs()
    self.doc.review_date = nowdate()
    set(self.doc, 'status', 'Pending Review')
    self.doc.save()
    return cstr('true')
  
  def reopen_task(self):
    set(self.doc, 'status', 'Open')
    self.doc.save()
    return cstr('true')
  
  def declare_completed(self):
    if self.doc.status == 'Open':
      self.validate_for_pending_review()
      self.doc.review_date = nowdate()
    else:
      self.validate_with_timesheet_dates()
    self.validate_for_closed()
    self.doc.closing_date = nowdate()
    set(self.doc, 'status', 'Closed')
    set(self.doc, 'docstatus', 1)
    self.doc.save()
    return cstr('true')
  
  def cancel_task(self):
    chk = sql("select distinct t1.name from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status!='Cancelled'", self.doc.name)
    if chk:
      chk_lst = [x[0] for x in chk]
      msgprint("Timesheet(s) "+','.join(chk_lst)+" created against this task. Thus can not be cancelled")
      raise Exception
    else:
      set(self.doc, 'status', 'Cancelled')
      set(self.doc, 'docstatus', 2)
    self.doc.save()
    return cstr('true')
  
  def on_cancel(self):
    self.cancel_task()