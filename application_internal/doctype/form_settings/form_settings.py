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
    self.doc = doc
    self.doclist = doclist

  def autoname(self):
    rep_nm = self.doc.doctype_name + '-' + 'Settings'
    if sql("select name from `tabForm Settings` where name=%s",rep_nm):
      msgprint("Settings for this form already created, please open existing form to do any changes.")
      raise Exception
    else:
      self.doc.name = rep_nm
      
  def get_filter_details(self,arg=''):
    dt_det = sql("select label, fieldtype, options, fieldname from tabDocField where parent=%s and label=%s",(self.doc.doctype_name,arg),as_dict=1)
        
    ret = {
      'field_label_fr' : dt_det and dt_det[0]['label'] or '',
      'field_type_fr'  : dt_det and dt_det[0]['fieldtype'] or '',
      'options_fr'     : dt_det and dt_det[0]['options'] or '',
      'field_name_fr'  : dt_det and dt_det[0]['fieldname'] or '',
      'table_name_fr'  : self.doc.doctype_name 
    }
    return cstr(ret)
    
  def get_field_details(self,arg=''):
    dt_det = sql("select label, fieldtype, options, fieldname from tabDocField where parent=%s and label=%s",(self.doc.doctype_name,arg),as_dict=1)
    ret = {
      'field_label_fd' : dt_det and dt_det[0]['label'] or '',
      'field_type_fd'  : dt_det and dt_det[0]['fieldtype'] or '',
      'options_fd'     : dt_det and dt_det[0]['options'] or '',
      'field_name_fd'  : dt_det and dt_det[0]['fieldname'] or '',
      'table_name_fd'  : self.doc.doctype_name 
    }
    return cstr(ret)    