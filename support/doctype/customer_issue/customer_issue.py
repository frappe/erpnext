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
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
    self.prefix = is_testing and 'test' or 'tab'
    
  def autoname(self):
    #self.doc.name = make_autoname('CI/' + self.doc.fiscal_year + '/.######')
    self.doc.name = make_autoname(self.doc.naming_series + '.######')
    
#check if maintenance schedule already generated
#============================================
  def check_maintenance_visit(self):
    nm = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Detail` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1 and t1.completion_status='Fully Completed'", self.doc.name)
    nm = nm and nm[0][0] or ''
    
    if not nm:
      return 'No'
  
  def on_submit(self):
    if session['user'] != 'Guest':
      if not self.doc.allocated_to:
        msgprint("Please select service person name whom you want to assign this issue")
        raise Exception
  
  def validate(self):
    if session['user'] != 'Guest' and not self.doc.customer:
      msgprint("Please select Customer from whom issue is raised")
      raise Exception
    #if not self.doc.email_id and not self.doc.contact_no:
    #  msgprint("Please specify contact no. and/or email_id")
    #  raise Exception
    #elif self.doc.email_id and not validate_email_add(self.doc.email_id.strip(' ')):
    #  msgprint('error:%s is not a valid email id' % self.doc.email_id)
    #  raise Exception
  
  def on_cancel(self):
    lst = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Detail` t2 where t2.parent = t1.name and t2.prevdoc_docname = '%s' and  t1.docstatus!=2"%(self.doc.name))
    if lst:
      lst1 = ','.join([x[0] for x in lst])
      msgprint("Maintenance Visit No. "+lst1+" already created against this customer issue. So can not be Cancelled")
      raise Exception
    else:
      set(self.doc, 'status', 'Cancelled')

  def on_update(self):
    pass
