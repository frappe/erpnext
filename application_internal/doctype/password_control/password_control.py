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
  def __init__(self, doc, doclist):
    self.doc = doc
    self.doclist = doclist
  
  def get_date_diff(self):
    if session['user'] != 'Administrator' and session['user'] != 'Demo':
      last_pwd_date = sql("select password_last_updated from tabProfile where name=%s",session['user'])[0][0] or ''
      if cstr(last_pwd_date) == '':
        sql("update tabProfile set password_last_updated = '%s' where name='%s'"% (nowdate(),session['user']))
      else:
        date_diff = (getdate(nowdate()) -last_pwd_date).days
        return date_diff
        
  def get_cur_pwd(self):
    if session['user'] != 'Administrator' and session['user'] != 'Demo':
      cur_pwd = sql("select password from tabProfile where name=%s",session['user'])[0][0] or ''
      return cur_pwd
      
  def reset_password(self,pwd):
    sql("update tabProfile set password= '%s',password_last_updated='%s' where name = '%s'" % (pwd,nowdate(),session['user']))