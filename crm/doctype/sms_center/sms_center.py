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
# ----------

class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
      
  def create_receiver_list(self):
    rec, where_clause = '', ''
    if self.doc.send_to == 'All Customer Contact':
      where_clause = self.doc.customer and " and customer = '%s'" % self.doc.customer or " and ifnull(is_customer, 0) = 1"
    if self.doc.send_to == 'All Supplier Contact':
      where_clause = self.doc.supplier and " and ifnull(is_supplier, 0) = 1 and supplier = '%s'" % self.doc.supplier or " and ifnull(is_supplier, 0) = 1"
    if self.doc.send_to == 'All Sales Partner Contact':
      where_clause = self.doc.sales_partner and " and ifnull(is_sales_partner, 0) = 1 and sales_aprtner = '%s'" % self.doc.sales_partner or " and ifnull(is_sales_partner, 0) = 1"
    msgprint(1)
    if self.doc.send_to in ['All Contact', 'All Customer Contact', 'All Supplier Contact', 'All Sales Partner Contact']:
      msgprint("select CONCAT(ifnull(first_name,''),'',ifnull(last_name,'')), mobile_no from `tabContact` where ifnull(mobile_no,'')!='' and docstatus != 2 %s" % where_clause)
      rec = sql("select CONCAT(ifnull(first_name,''),'',ifnull(last_name,'')), mobile_no from `tabContact` where ifnull(mobile_no,'')!='' and docstatus != 2 %s" % where_clause)
    elif self.doc.send_to == 'All Lead (Open)':
      rec = sql("select lead_name, mobile_no from tabLead where ifnull(mobile_no,'')!='' and docstatus != 2 and status = 'Open'")
    elif self.doc.send_to == 'All Employee (Active)':
      where_clause = self.doc.department and " and t1.department = '%s'" % self.doc.department or ""
      where_clause += self.doc.branch and " and t1.branch = '%s'" % self.doc.branch or ""
      rec = sql("select t1.employee_name, t2.cell_number from `tabEmployee` t1, `tabEmployee Profile` t2 where t2.employee = t1.name and t1.status = 'Active' and t1.docstatus != 2 and ifnull(t2.cell_number,'')!='' %s" % where_clause)
    elif self.doc.send_to == 'All Sales Person':
      rec = sql("select sales_person_name, mobile_no from `tabSales Person` where docstatus != 2 and ifnull(mobile_no,'')!=''")

    rec_list = ''
    for d in rec:
      rec_list += d[0] + ' - ' + d[1] + '\n'
    self.doc.receiver_list = rec_list

  def get_receiver_nos(self):
    receiver_nos = []
    for d in self.doc.receiver_list.split('\n'):
      receiver_no = d
      if '-' in d:
        receiver_no = receiver_no.split('-')[1]
      if receiver_no.strip():
        receiver_nos.append(cstr(receiver_no).strip())
    return receiver_nos

  def send_sms(self):
    if not self.doc.message:
      msgprint("Please enter message before sending")
    else:
      receiver_list = self.get_receiver_nos()
      if receiver_list:
        msgprint(get_obj('SMS Control', 'SMS Control').send_sms(receiver_list, cstr(self.doc.message)))
