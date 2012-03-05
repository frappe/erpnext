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
    
  def enable_login(self,arg):
    arg = eval(arg)
    sql("update tabContact set disable_login = 'No' where name=%s",arg['contact'])
    sql("update tabProfile set enabled=1 where name=%s",arg['email'])
    
  def disable_login(self,arg):
    arg = eval(arg)
    sql("update tabContact set disable_login = 'Yes' where name=%s",arg['contact'])
    sql("update tabProfile set enabled=0 where name=%s",arg['email'])
    
  def create_login(self,arg):
    arg = eval(arg)
    cont_det = sql("select * from tabContact where name=%s",(arg['contact']),as_dict=1)
    if cont_det[0]['docstatus'] !=0:
      msgprint('Please save the corresponding contact first')
      raise Exception
      
    if sql("select name from tabProfile where name=%s",cont_det[0]['email_id']):
      msgprint('Profile with same name already exist.')
      raise Exception
    else:
      p = Document('Profile')
      p.name = cont_det[0]['email_id']
      p.first_name = cont_det[0]['first_name']
      p.last_name = cont_det[0]['last_name']
      p.email = cont_det[0]['email_id']
      p.cell_no = cont_det[0]['contact_no']
      p.password = 'password'
      p.enabled = 1
      p.user_type = 'Partner';
      p.save(1)
      
      get_obj(doc=p).on_update()
      
      role = []
      if cont_det[0]['contact_type'] == 'Individual':
        role = ['Customer']
      else:
        if cont_det[0]['is_customer']:
          role.append('Customer')
        if cont_det[0]['is_supplier']:
          role.append('Supplier')
        if cont_det[0]['is_sales_partner']:
          role.append('Partner')

      if role:
        prof_nm = p.name
        for i in role:
          r = Document('UserRole')
          r.parent = p.name
          r.role = i
          r.parenttype = 'Profile'
          r.parentfield = 'userroles'
          r.save(1)
        
          if i == 'Customer':
            def_keys = ['from_company','customer_name','customer']
            def_val = cont_det[0]['customer_name']
            self.set_default_val(def_keys,def_val,prof_nm)

          if i == 'Supplier':
            def_keys = ['supplier_name','supplier']
            def_val = cont_det[0]['supplier_name']
            self.set_default_val(def_keys,def_val,prof_nm)

      sql("update tabContact set has_login = 'Yes' where name=%s",cont_det[0]['name'])
      sql("update tabContact set disable_login = 'No' where name=%s",cont_det[0]['name'])
      msgprint('User login is created.')
      
 #------set default values---------
  def set_default_val(self,def_keys,def_val,prof_nm):
    for d in def_keys:
      kv = Document('DefaultValue')
      kv.defkey = d
      kv.defvalue = def_val
      kv.parent = prof_nm
      kv.parenttype = 'Profile'
      kv.parentfield = 'defaults'
      kv.save(1)