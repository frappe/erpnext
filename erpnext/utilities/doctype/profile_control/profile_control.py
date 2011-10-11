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
    self.last_profile = None
  
  # Sync Profile with Gateway
  # -------------------------
  def sync_with_gateway(self,pid):
    p = Document('Profile',pid)

    # login to gateway
    from webnotes.utils.webservice import FrameworkServer
    fw = FrameworkServer('www.erpnext.com','/','__system@webnotestech.com','password',https=1)

    account_id = sql("select value from tabSingles where doctype='Control Panel' and field='account_id'")[0][0]
    
    # call add profile
    ret = fw.runserverobj('Profile Control','Profile Control','add_profile_gateway',str([p.first_name, p.middle_name, p.last_name, p.email, p.name, account_id]))
    
    if ret.get('exc'):
      msgprint(ret['exc'])
      raise Exception
  
  def get_role_permission(self,role):
    perm = sql("select distinct t1.`parent`, t1.`read`, t1.`write`, t1.`create`, t1.`submit`,t1.`cancel`,t1.`amend` from `tabDocPerm` t1, `tabDocType` t2 where t1.`role` ='%s' and t1.docstatus !=2 and t1.permlevel = 0 and t1.`read` = 1 and t2.module != 'Recycle Bin' and t1.parent=t2.name "%role)
    return perm or ''
  
  
  # Check if password is expired
  # --------------------------------
  def has_pwd_expired(self):
    if session['user'] != 'Administrator' and session['user'].lower() != 'demo':
      last_pwd_date = None
      try:
        last_pwd_date = sql("select password_last_updated from tabProfile where name=%s",session['user'])[0][0] or ''
      except:
        return 'No'
      if cstr(last_pwd_date) == '':
        sql("update tabProfile set password_last_updated = '%s' where name='%s'"% (nowdate(),session['user']))
        return 'No'
      else:
        date_diff = (getdate(nowdate()) - last_pwd_date).days
        expiry_period = sql("select value from tabSingles where doctype='Control Panel' and field='password_expiry_days'")
        if expiry_period and cint(expiry_period[0][0]) and cint(expiry_period[0][0]) < date_diff:
          return 'Yes'
        return 'No'
              
  def reset_password(self,pwd):
    if sql("select name from tabProfile where password=PASSWORD(%s) and name=%s", (pwd,session['user'])):
      return 'Password cannot be same as old password'
    sql("update tabProfile set password=PASSWORD(%s),password_last_updated=%s where name = %s", (pwd,nowdate(),session['user']))
    return 'ok'
  
#-------------------------------------------------------------------------------------------------------
  #functions for manage user page
  #-----------Enable/Disable Profile-----------------------------------------------------------------------------------------------    
  def change_login(self,args):
    args = eval(args)
    
    if cint(args['set_disabled'])==0:
      sql("update `tabProfile` set enabled=1 where name='%s'"%args['user'])
    else:
      sql("update `tabProfile` set enabled=0 where name='%s'"%args['user'])
    
    return 'ok'

#------------return role list -------------------------------------------------------------------------------------------------
  # All roles of Role Master
  def get_role(self):
    r_list=sql("select name from `tabRole` where name not in ('Administrator','All','Guest')")
    if r_list[0][0]:
      r_list = [x[0] for x in r_list]
    return r_list
    
  # Only user specific role
  def get_user_role(self,usr):
    r_list=sql("select role from `tabUserRole` where parent=%s and role not in ('Administrator','All','Guest')",usr)
    if r_list[0][0]:
      r_list = [x[0] for x in r_list]
    else:
      r_list=[]
    return r_list
  
  # adding new role
  def add_user_role(self,args):
    arg=eval(args)
    sql("delete from `tabUserRole` where parenttype='Profile' and parent ='%s'" % (cstr(arg['user'])))
    role_list = arg['role_list'].split(',')
    for r in role_list:
      pr=Document('UserRole')
      pr.parent = arg['user']
      pr.parenttype = 'Profile'
      pr.role = r
      pr.parentfield = 'userroles'
      pr.save(1)
      


  # Add new member
  # ---------------
  def add_profile(self,arg):
    
    # Check credit balance
    get_obj('WN ERP Client Control').check_credit_balance()
    
    arg=eval(arg)
    pr=Document('Profile')
    for d in arg.keys():
      if d!='role':
        pr.fields[d] = arg[d]
   
    pr.enabled=0
    pr.user_type='System User'
    pr.save(1)
    pr_obj = get_obj('Profile',pr.name)
    if (pr.name):
      msg="New member is added"
      pr_obj.on_update()
    else:
      msg="Profile not created"
    
    return cstr(msg)

  # to find currently login user 
  def current_login(self):
    cl_list=sql("select distinct user from tabSessions")
    if cl_list:
      cl_list=[x[0] for x in cl_list]
    
    return cl_list


  # Remove Profile
  # ---------------
  def remove_profile(self, user):
    # delete profile
    webnotes.model.delete_doc('Profile',user)
    
    # Update WN ERP Client Control
    sql("update tabSingles set value = value - 1 where field = 'total_users' and doctype = 'WN ERP Client Control'")

    # login to gateway
    from webnotes.utils.webservice import FrameworkServer
    fw = FrameworkServer('www.erpnext.com','/','__system@webnotestech.com','password',https=1)

    account_id = sql("select value from tabSingles where doctype='Control Panel' and field='account_id'")[0][0]

    # call remove profile
    ret = fw.runserverobj('Profile Control','Profile Control','remove_app_sub',str([user, account_id, session['user']]))
    
    if ret.get('exc'):
      msgprint(ret['exc'])
      raise Exception

    return "User Removed Successfully"


  # Create Profile
  # ---------------
  def create_profile(self, email):
    if sql("select name from tabProfile where name = %s", email):
      sql("update tabProfile set docstatus = 0 where name = %s", email)
    else:
      pr = Document('Profile')
      pr.email = email
      pr.enabled=0
      pr.user_type='System User'
      pr.save(1)
