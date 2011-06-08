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
      
  def create_receiver_table(self):
    if self.doc.send_to:
      self.doc.clear_table(self.doclist, 'receiver_details')
      rec = ''
      if self.doc.send_to == 'All Customer':
        rec = sql("select customer_name, CONCAT(ifnull(first_name,''),'',ifnull(last_name,'')), mobile_no from `tabContact` where ifnull(customer_name,'') !='' and ifnull(mobile_no,'')!=''")

      elif self.doc.send_to == 'Customer Group' and self.doc.customer_group_name:
       
        rec = sql("select t2.customer_name, CONCAT(ifnull(first_name,''),'',ifnull(last_name,'')), t1.mobile_no from `tabContact` t1, `tabCustomer` t2 where t2.name = t1.customer_name and ifnull(t1.mobile_no,'')!='' and t2.customer_group = '%s'"%self.doc.customer_group_name)
      if not rec:
        msgprint("Either customer having no contact or customer's contact does not have mobile no")
        raise Exception 

      for d in rec:
        ch = addchild(self.doc, 'receiver_details', 'Receiver Detail', 1, self.doclist)
        ch.customer_name = d[0]
        ch.receiver_name = d[1]
        ch.mobile_no = d[2]
    else:
      msgprint("Please select 'Send To' field")
        
        
  def send_sms(self):
    if not self.doc.message:
      msgprint("Please type the message before sending")
    elif not getlist(self.doclist, 'receiver_details'):
      msgprint("Receiver Table is blank.")
    else:
      receiver_list = []
      for d in getlist(self.doclist, 'receiver_details'):
        if d.mobile_no:
          receiver_list.append(d.mobile_no)
      if receiver_list:
        msgprint(get_obj('SMS Control', 'SMS Control').send_sms(receiver_list, self.doc.message))