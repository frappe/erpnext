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
    self.doc, self.doclist = d,dl

  # get the code
  # ------------
  def get_code(self, arg):
    dt, dn, field = arg.split('~~~')
    return [str(r or '') for r in sql("select `%s`, modified from `tab%s` where name='%s'" % (field, dt, dn))[0]]
  
  # set code
  # check modified, add to history, update code
  # -------------------------------------------
  def set_code(self, arg):
    dt, dn, field, comment, modified = arg.split('~~~')

    # validate modified
    old_modified = sql("select modified from `tab%s` where name='%s'" % (dt, dn))[0][0]
    if str(old_modified) != modified:
       msgprint('error:Someone has updated the code after you checked it out. Please update to the latest copy of the code before saving.')
       raise Exception

    # add to history
    if self.doc.add_to_history:
      self.add_to_history(dt, dn, field, self.doc.code, comment)

    # update
    new_modified = now()
    sql("update `tab%s` set `%s` = %s, modified = %s where name=%s" % (dt, field, '%s', '%s', '%s'), (self.doc.code, new_modified, dn))

    # compile
    if dt=='DocType':
      get_obj('DocType',dn).compile_code()
      sql("delete from __DocTypeCache where name=%s", dn)

    msgprint('ok:Saved')
    return new_modified

  # get properties
  # --------------
  def get_properties(self, arg=''):
    #return convert_to_lists(sql("select fieldname, label, fieldtype, options from tabDocField where parent=%s and ifnull(fieldname,'') != '' order by idx asc", self.doc.select_doctype))
    return convert_to_lists(sql("select fieldname, label, fieldtype, options from tabDocField where parent=%s and ifnull(label,'') != '' order by idx asc", self.doc.select_doctype))
  # add to history
  # --------------
  def add_to_history(self, dt, dn, fn, code, comment):
    ch = Document('Code History')
    ch.script_from = dt
    ch.record_id = dn
    ch.field_name = fn
    ch.comment = comment
    ch.code = code
    ch.save(1)
    