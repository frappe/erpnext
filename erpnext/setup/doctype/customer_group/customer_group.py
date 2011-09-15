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
    self.nsm_parent_field = 'parent_customer_group';


  # update Node Set Model
  def update_nsm_model(self):
    import webnotes
    import webnotes.utils.nestedset
    webnotes.utils.nestedset.update_nsm(self)

  # ON UPDATE
  #--------------------------------------
  def on_update(self):
    # update nsm
    self.update_nsm_model()   


  def validate(self): 

    r = sql("select name from `tabCustomer Group` where name = '%s' and docstatus = 2"%(self.doc.customer_group_name))
    if r:
      msgprint("%s record is trashed. To untrash please go to Setup & click on Trash."%(self.doc.customer_group_name))
      raise Exception