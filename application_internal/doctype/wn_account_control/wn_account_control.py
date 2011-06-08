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
  def __init__(self,doc,doclist):
    self.doc = doc
    self.doclist = doclist

  def get_users(self):
    ret = sql("select name from tabProfile where name!='Administrator' and name!='Guest' and enabled=1")
    return ret

  def remove_users(self,args):
    args = eval(args)
    #for user in args['app_user_list']:
      #sql("update tabProfile set enabled=0 where email=%s",(user))

  def create_users_profile(self,args):
    args = eval(args)
    for email_id in args['user_email_ids']:
      if sql("select email from tabProfile where email=%s",(email_id)):
        p = Document('Profile',email_id)
        p.enabled = 1
        p.save()
      else:  
        p = Document('Profile')
        p.email = email_id
        p.save(1)