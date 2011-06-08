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
  def __init__(self,d,dl):
    self.doc = d
    self.doclist = dl
  
  def get_wiki_detail(self,arg):
    arg = eval(arg)
    ret = {}
    latest_revision = sql("select max(revision) from `tabWiki History` where reference=%s", arg['dn'])[0][0]
    
    ret['detail'] = convert_to_lists(sql("select revision, modified_by,creation from `tabWiki History` where reference=%s and revision=%s", (arg['dn'],latest_revision)))
    ret['contributors'] = convert_to_lists(sql("select distinct modified_by from `tabWiki History` where reference=%s", arg['dn']))
    return ret