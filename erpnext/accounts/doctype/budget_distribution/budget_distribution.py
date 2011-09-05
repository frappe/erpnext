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
    self.doc,self.doclist = doc,doclist
    
  def get_months(self):
    month_list = ['January','February','March','April','May','June','July','August','September','October','November','December']
    idx =1
    for m in month_list:
      mnth = addchild(self.doc,'budget_distribution_details','Budget Distribution Detail',1,self.doclist)
      mnth.month = m or ''
      mnth.idx = idx
      idx += 1
      
  def validate(self):
    total = 0
    for d in getlist(self.doclist,'budget_distribution_details'):
      total = flt(total) + flt(d.percentage_allocation)
    if total > 100:
      msgprint("Percentage Allocation should not exceed 100%.")
      raise Exception
    elif total < 100:
      msgprint("Percentage Allocation should not recede 100%.")
      raise Exception