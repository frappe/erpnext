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
    self.nsm_parent_field = 'parent_cost_center'
        
  def autoname(self):
    #company_abbr = sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
    self.doc.name = self.doc.cost_center_name + ' - ' + self.doc.company_abbr    
      
  def get_abbr(self):
    abbr = sql("select abbr from tabCompany where company_name='%s'"%(self.doc.company_name))[0][0] or ''
    ret = {
      'company_abbr'  : abbr
    }
    return ret

  def validate(self): 
    # Cost Center name must be unique
    # ---------------------------
    if (self.doc.__islocal or (not self.doc.name)) and sql("select name from `tabCost Center` where cost_center_name = %s and company_name=%s", (self.doc.cost_center_name, self.doc.company_name)):
      msgprint("Cost Center Name already exists, please rename")
      raise Exception
      
    check_acc_list = []
    for d in getlist(self.doclist, 'budget_details'):
      if [d.account, d.fiscal_year] in check_acc_list:
        msgprint("Account " + cstr(d.account) + "has been entered more than once for fiscal year " + cstr(d.fiscal_year))
        raise Exception
      if [d.account, d.fiscal_year] not in check_acc_list: check_acc_list.append([d.account, d.fiscal_year])
      
  def on_update(self):
    # update Node Set Model
    import webnotes
    import webnotes.utils.nestedset
    # update Node Set Model
    webnotes.utils.nestedset.update_nsm(self)  
    
  def check_if_child_exists(self):
    return sql("select name from `tabCost Center` where parent_cost_center = %s and docstatus != 2", self.doc.name, debug=0)
    
  # On Trash
  # --------
  def on_trash(self):
    if self.check_if_child_exists():
      msgprint("Child exists for this cost center. You can not trash this account.", raise_exception=1)      
      
    # rebuild tree
    set(self.doc,'old_parent', '')
    self.update_nsm_model()
