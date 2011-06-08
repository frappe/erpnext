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
    self.doc, self.doclist = doc, doclist
    
  
  def apply_rule(self,form_obj):
    #msgprint("hello")
    rule_list = sql("select rule_name from `tabWorkflow Rule` where select_form = '%s' and rule_status='Active' order by rule_priority asc" % (form_obj.doc.doctype))
    for rl in rule_list:
      #msgprint(rl[0])
      autho_obj=get_obj("Workflow Rule",rl[0],with_children=1)   
      cond_hold = autho_obj.evalute_rule(form_obj)
      #msgprint("cond_hold:" + cond_hold)
      if cond_hold =='Yes':
        self.apply_action(rl[0],form_obj)
    return
      
 
  #if rule holds true then the following action will be taken
  def apply_action(self,rule_no,form_obj):
    rule_obj=get_obj('Workflow Rule',rule_no,with_children=1)
    #msgprint("action")
    for d in getlist(rule_obj.doclist,'workflow_action_details'):
      field_name=sql("select fieldname from tabDocField where parent='%s' and label='%s'" %(form_obj.doc.doctype,d.action_field))[0][0]
      if field_name:
        #msgprint(field_name)
        form_obj.doc.fields[field_name] = d.action_value
    return