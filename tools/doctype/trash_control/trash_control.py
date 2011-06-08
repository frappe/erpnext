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
  def __init__(self, d, dl):
    self.doc, self.doclist = d, dl

  
  # Get Masters
  # -----------
  def get_masters(self):
    mlist = []
    res = sql("select distinct t1.name from tabDocType t1, tabDocPerm t2 where ifnull(t1.allow_trash, 0) = 1 and (ifnull(t2.write, 0) = 1 or ifnull(t2.create, 0) = 1) and t2.role in %s and t2.parent = t1.name and t1.module not in ('DocType','Application Internal','Recycle Bin','Development','Testing','Testing System','Test') ORDER BY t1.name" % cstr(tuple(webnotes.user.get_roles())))
    for r in res:
      mlist.append(r[0])
    return mlist


  # Get Trash Records
  # -----------------
  def get_trash_records(self, mast_name):
    mlist = []
    rec_dict = {}
    if mast_name == 'All':
      mlist = self.get_masters()
    else:
      mlist.append(mast_name)
    for i in mlist:
      rec = [r[0] for r in sql("select name from `tab%s` where docstatus = 2" % i)]
      if rec:
        rec_dict[i] = rec
    return rec_dict


  # Restore Records
  # ---------------
  def restore_records(self, arg):
    arg = eval(arg)
    for k in arg:
      for r in arg[k]:
        sql("update `tab%s` set docstatus = 0, modified = '%s', trash_reason = '' where name = '%s'" % (k, now(), r))
        dt_obj = get_obj(k,r)
        if hasattr(dt_obj, 'on_restore'): dt_obj.on_restore()