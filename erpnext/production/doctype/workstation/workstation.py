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

  def update_bom_operation(self):
      bom_list = sql(" select DISTINCT parent from `tabBOM Operation` where workstation = '%s'" % self.doc.name)
      for bom_no in bom_list:
        sql("update `tabBOM Operation` set hour_rate = '%s' where parent = '%s' and workstation = '%s'"%( self.doc.hour_rate, bom_no[0], self.doc.name))
  
  def on_update(self):
    set(self.doc, 'overhead', flt(self.doc.hour_rate_electricity) + flt(self.doc.hour_rate_consumable) + flt(self.doc.hour_rate_rent))
    set(self.doc, 'hour_rate', flt(self.doc.hour_rate_labour) + flt(self.doc.overhead))
    self.update_bom_operation()