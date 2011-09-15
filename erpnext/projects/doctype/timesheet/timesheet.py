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
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  def get_customer_details(self, project_name):
    cust = sql("select customer, customer_name from `tabProject` where name = %s", project_name)
    if cust:
      ret = {'customer': cust and cust[0][0] or '', 'customer_name': cust and cust[0][1] or ''}
      return (ret)
  
  def get_task_details(self, task_sub):
    tsk = sql("select name, project, customer, customer_name from `tabTicket` where subject = %s", task_sub)
    if tsk:
      ret = {'task_id': tsk and tsk[0][0] or '', 'project_name': tsk and tsk[0][1] or '', 'customer_name': tsk and tsk[0][3] or ''}
      return ret
  
  def validate(self):
    if getdate(self.doc.timesheet_date) > getdate(nowdate()):
      msgprint("You can not prepare timesheet for future date")
      raise Exception
    
    chk = sql("select name from `tabTimesheet` where timesheet_date=%s and owner=%s and status!='Cancelled' and name!=%s", (self.doc.timesheet_date, self.doc.owner, self.doc.name))
    if chk:
      msgprint("You have already created timesheet "+ cstr(chk and chk[0][0] or '')+" for this date.")
      raise Exception

    import time
    for d in getlist(self.doclist, 'timesheet_details'):
      if d.act_start_time and d.act_end_time:
        d1 = time.strptime(d.act_start_time, "%H:%M")
        d2 = time.strptime(d.act_end_time, "%H:%M")
        
        if d1 > d2:
          msgprint("Start time can not be greater than end time. Check for Task Id : "+cstr(d.task_id))
          raise Exception
        elif d1 == d2:
          msgprint("Start time and end time can not be same. Check for Task Id : "+cstr(d.task_id))
          raise Exception
  
  def calculate_total_hr(self):
    import datetime
    import time
    for d in getlist(self.doclist, 'timesheet_details'):
      x1 = d.act_start_time.split(":")
      x2 = d.act_end_time.split(":")
      
      d1 = datetime.timedelta(minutes=cint(x1[1]), hours=cint(x1[0]))      
      d2 = datetime.timedelta(minutes=cint(x2[1]), hours=cint(x2[0]))
      d3 = (d2 - d1).seconds
      d.act_total_hrs = time.strftime("%H:%M", time.gmtime(d3))
      sql("update `tabTimesheet Detail` set act_total_hrs = %s where parent=%s and name=%s", (d.act_total_hrs,self.doc.name,d.name))
  
  def on_update(self):
    self.calculate_total_hr()
    set(self.doc, 'status', 'Draft')
  
  def on_submit(self):
    set(self.doc, 'status', 'Submitted')
  
  def on_cancel(self):
    set(self.doc, 'status', 'Cancelled')