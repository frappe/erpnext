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

  def update_series(self):
    series = sql("select name,current from `tabSeries` where name = %s", self.doc.prefix,as_dict = 1)
    if series:
      msgprint("This is going to update Series with Prefix : " + series[0]['name'] + " from Current : " + cstr(series[0]['current']) + " to Current : "+ cstr(self.doc.current))
      sql("update `tabSeries` set current = '%s' where name = '%s'" % (self.doc.current,series[0]['name']))
      msgprint("Series Updated Successfully")
    else:
      msgprint("Please Check Prefix as there is no such Prefix : "+ self.doc.prefix +" Or Try Insert Button")

  def insert_series(self):
    #sql("start transaction")
    series = sql("select name,current from `tabSeries` where name = %s", self.doc.prefix, as_dict = 1)
    if series:
      msgprint("Series with Prefix : " + series[0]['name'] + "already in the system . Try Update Button")
    else:
      msgprint("This is going to Insert Series with Prefix : " + cstr(self.doc.prefix) + " Current: " + cstr(self.doc.current))
      sql("insert into `tabSeries` (name,current) values ('%s','%s')" % (self.doc.prefix, self.doc.current))
      msgprint("Series Inserted Successfully")
