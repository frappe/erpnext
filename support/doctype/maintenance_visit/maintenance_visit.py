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
  
  #get item details
  #------------------
  def get_item_details(self, item_code):
    item = sql("select item_name,description from `tabItem` where name = '%s'" %(item_code), as_dict=1)
    ret = {
      'item_name' : item and item[0]['item_name'] or '',
      'description' : item and item[0]['description'] or ''
    }
    return ret
  
  # fetch details of resp Sales order or customer issue
  #-----------------------------------------------------------
  def fetch_items(self):
    if self.doc.sales_order_no and self.doc.customer_issue_no:
      msgprint("You can not fetch details of both, Sales Order and Customer Issue, in same Maintenance Visit")
      raise Exception
    
    self.doc.clear_table(self.doclist, 'maintenance_visit_details')
    
    if self.doc.sales_order_no:
      self.doclist = get_obj('DocType Mapper', 'Sales Order-Maintenance Visit').dt_map('Sales Order', 'Maintenance Visit', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Maintenance Visit'],['Sales Order Detail', 'Maintenance Visit Detail']]")
    
    elif self.doc.customer_issue_no:      
      self.doclist = get_obj('DocType Mapper', 'Customer Issue-Maintenance Visit').dt_map('Customer Issue', 'Maintenance Visit', self.doc.customer_issue_no, self.doc, self.doclist, "[['Customer Issue', 'Maintenance Visit'],['Customer Issue', 'Maintenance Visit Detail']]")
  
  #validate reference value using doctype mapper
  #-----------------------------------------------------
  def validate_reference_value(self, check_for):
    if check_for == 'Sales Order':
      get_obj('DocType Mapper', 'Sales Order-Maintenance Visit', with_children = 1).validate_reference_value(self, self.doc.name)
    elif check_for == 'Customer Issue':
      get_obj('DocType Mapper', 'Customer Issue-Maintenance Visit', with_children = 1).validate_reference_value(self, self.doc.name)
  
  #check if serial no exist in system
  #--------------------------------------
  def validate_serial_no(self):
    for d in getlist(self.doclist, 'maintenance_visit_details'):
      if d.serial_no and not sql("select name from `tabSerial No` where name = '%s' and docstatus != 2" % d.serial_no):
        msgprint("Serial No: "+ d.serial_no + " not exists in the system")
        raise Exception
      #elif not d.serial_no and d.item_code:
      #  ser = sql("select has_serial_no from tabItem where name = '%s'" % d.item_code)
      #  ser = ser and ser[0][0] or 'No'
      #  if ser == 'Yes':
      #    msgprint("Serial No is mandatory for item: " + d.item_code)
      #    raise Exception
  
  def validate(self):
    if not getlist(self.doclist, 'maintenance_visit_details'):
      msgprint("Please enter maintenance details")
      raise Exception
    
    for d in getlist(self.doclist, 'maintenance_visit_details'):
      if d.prevdoc_doctype == 'Sales Order':
        check_for = 'Sales Order'
      elif d.prevdoc_doctype == 'Customer Issue':
        check_for = 'Customer Issue'
      else:
        msgprint("Maintenance Visit must be created either against Sales Order or against Customer Issue")
        raise Exception
    
    if check_for:
      self.validate_reference_value(check_for)

    self.validate_serial_no()
  
  def update_customer_issue(self, flag):
    for d in getlist(self.doclist, 'maintenance_visit_details'):
      if d.prevdoc_docname and d.prevdoc_doctype == 'Customer Issue' :
        if flag==1:
          mntc_date = self.doc.mntc_date
          service_person = d.service_person
          work_done = d.work_done
          if self.doc.completion_status == 'Fully Completed':
            status = 'Closed'
          elif self.doc.completion_status == 'Partially Completed':
            status = 'Work In Progress'
        else:
          nm = sql("select t1.name, t1.mntc_date, t2.service_person, t2.work_done from `tabMaintenance Visit` t1, `tabMaintenance Visit Detail` t2 where t2.parent = t1.name and t1.completion_status = 'Partially Completed' and t2.prevdoc_docname = %s and t1.name!=%s and t1.docstatus = 1 order by t1.name desc limit 1", (d.prevdoc_docname, self.doc.name))
          
          if nm:
            status = 'Work In Progress'
            mntc_date = nm and nm[0][1] or ''
            service_person = nm and nm[0][2] or ''
            work_done = nm and nm[0][3] or ''
          else:
            status = 'Open'
            mntc_date = ''
            service_person = ''
            work_done = ''
        
        sql("update `tabCustomer Issue` set resolution_date=%s, resolved_by=%s, resolution_details=%s, status=%s where name =%s",(mntc_date,service_person,work_done,status,d.prevdoc_docname))
  
  # check if last maintenance visit against same sales order/ customer issue
  #-----------------------------------------------------------------------------------
  def check_if_last_visit(self):
    for d in getlist(self.doclist, 'maintenance_visit_details'):
      if d.prevdoc_docname:
        check_for_docname = d.prevdoc_docname
        check_for_doctype = d.prevdoc_doctype
    
    if check_for_docname:
      check = sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Detail` t2 where t2.parent = t1.name and t1.name!=%s and t2.prevdoc_docname=%s and t1.docstatus = 1 and (t1.mntc_date > %s or (t1.mntc_date = %s and t1.mntc_time > %s))", (self.doc.name, check_for_docname, self.doc.mntc_date, self.doc.mntc_date, self.doc.mntc_time))
      
      if check:
        check_lst = [x[0] for x in check]
        check_lst =','.join(check_lst)
        msgprint("To cancel this, you need to cancel Maintenance Visit(s) "+cstr(check_lst)+" created after this maintenance visit against same "+check_for_doctype)
        raise Exception
      else:
        self.update_customer_issue(0)
  
  def on_submit(self):
    self.update_customer_issue(1)    
    set(self.doc, 'status', 'Submitted')
  
  def on_cancel(self):
    self.check_if_last_visit()    
    set(self.doc, 'status', 'Cancelled')

  def on_update(self):
    pass
    
