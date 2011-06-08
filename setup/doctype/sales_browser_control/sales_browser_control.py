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
 
  #=============================================================================================
  def get_record_list(self,arg):

    parent, type = arg.split(',')
    pt_col = "parent_"+type.replace(' ','_').lower()
   
    cl = sql("select name,is_group from `tab%s` where docstatus != 2 and %s ='%s' order by is_group desc"%(type,pt_col,parent),as_dict=1)

    return {'parent':parent, 'cl':cl}

  #=============================================================================================  
  # --------get root level records like all territories, all sales person etc---------  
  def get_fl_node(self,arg):

    pt_col = "parent_"+arg.replace(' ','_').lower()
    cl = sql("select name,is_group from `tab%s` where docstatus !=2 and %s=''"%(arg,pt_col),as_dict=1)
    return {'cl':cl}

  #=============================================================================================
  def add_node(self,arg):
    arg = eval(arg)
    node_title = arg['node_title']
    n = Document(node_title)
    for d in arg.keys():
      if d != 'node_title':
        n.fields[d]=arg[d]
    n.old_parent = ''      
    n_obj = get_obj(doc=n)

    n_obj.validate()

    n_obj.doc.save(1)

    n_obj.on_update()

    return n_obj.doc.name
      
  #=============================================================================================
  def trash_record(self,arg):  
    name,type = arg.split(',')
    
    #validation for trash of default record
    if not type == 'Sales Person':
      field = 'default_'+type.lower().replace(' ','_')
      chk = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = '%s' and value = '%s'"%(field,name))
      if chk:
        msgprint("'%s' record is set as a default %s in Global Defaults. Please change default %s then try to trash '%s' record."%(name,type.lower(), type.lower(), name))
        raise Exception
    
    
    res = sql("select t1.name from `tab%s` t1, `tab%s` t2 where t1.lft > t2.lft and t1.rgt < t2.rgt and t1.docstatus != 2 and t2.name = '%s'"%(type,type,name))
    if res:
      msgprint("You can not trashed %s as it contains other nodes."%name)
      raise Exception
      

    sql("update `tab%s` set docstatus = 2 where name = '%s'"%(type,name))

  #=============================================================================================    
  def get_parent_lst(self,type):
    par_lst = [r[0] for r in sql("select name from `tab%s` where is_group = 'Yes' and docstatus != 2"%type)]
    return par_lst
 
  #=============================================================================================
  def get_record(self,arg):

    name, type = arg.split(',')

    dict1 = {'Territory':'parent_territory','Customer Group':'parent_customer_group','Item Group':'parent_item_group','Sales Person':'parent_sales_person'}
    
    parent_name = dict1[type]
    
    query ="select name,"+dict1[type]+",is_group,rgt,lft from `tab"+cstr(type)+"` where name = '%s'"
  
    sv = sql(query%(cstr(name)))
 
 
    par_lst = [r[0] for r in sql("select distinct name from `tab"+cstr(type)+"` where docstatus !=2 and (rgt > %s or lft < %s) and is_group='Yes'"%(sv[0][3],sv[0][4]))]
 
    dict2 = {}
    dict2['name']=sv[0][0]
    dict2['parent']=cstr(sv[0][1])
    dict2['parent_lst']=par_lst
    dict2['is_group']=sv[0][2]

    return dict2
    
  #=============================================================================================
  def edit_node(self,arg):
    arg = eval(arg)
    nt = arg['node_title']

    nm = nt == 'Territory' and arg['territory_name'] or nt == 'Sales Person' and arg['sales_person_name'] or nt=='Item Group' and arg['item_group_name'] or nt =='Customer Group' and arg['customer_group_name'] or ''
    
    n_obj = get_obj(nt,nm) 
    for d in arg.keys():
      if d != 'node_title':
        n_obj.doc.fields[d]=arg[d]
   
    n_obj.doc.save()
    n_obj.on_update()
   
  
  #=============== validation ======================================================================================

  def mvalidate(self,args):

    r = eval(args)
    
    if r['lft'] == 0:
      n = sql("select lft,rgt from `tab%s` where name = '%s'"%(r['node_title'],r['nm']))
      r['lft'] = n[0][0]
      r['rgt'] = n[0][1]
    
    if r['action'] == 'Update':
      #-----------------validate if current node has child node----------------------------------
      v1 = self.val_group(r) 
      if v1 == 'true': return 'true' 

      
      #-------------------validation for parent sales person cannot be his child node------------
      v1 = self.val_prt(r) 
      if v1 == 'true': return 'true'     
      
      #--------if current record has set as default record in manage account then should not allow to change 'has child node' to 'yes'
      v1 = self.group_changed(r) 
      if v1 == 'true': return 'true'     
      
    elif r['action'] == 'Create':
      #-------------------validation - record is already exist--------------------------------
      v1 = self.duplicate_rcd(r)

      if v1 == 'true': return 'true' 
      
      #-------------------------------------------------
      v1 = self.trash_rcd(r)
      if v1 == 'true': return 'true' 

    return 'false'     
  #-----------------validate if current node has child node----------------------------------
  #------------------if yes then cannot change current node from group to leaf
  #ON EDIT
  def val_group(self,r):
    if r['is_group'] == 'No':
      ch = sql("select name from `tab%s` where lft>%s and rgt<%s and docstatus != 2"%(r['node_title'],r['lft'],r['rgt']))
      if ch:
        msgprint("You can not changed %s from group to leaf node as it contains other nodes."%r['nm'])    
        return 'true'
    return 'false'  
    
   #-------------------validation for parent sales person cannot be his child node-------------               
   #ON EDIT
  def val_prt(self,r):
    res = sql("select name from `tab%s` where is_group = 'Yes' and docstatus!= 2 and (rgt > %s or lft < %s) and name ='%s' and name !='%s'"%(r['node_title'],r['rgt'],r['lft'],r['parent_nm'],r['nm']))

    if not res:
      msgprint("Please enter parent %s."%(r['node_title'])) 
      return 'true'
    return 'false'
      
  #--------if current record has set as default record then not allowed to changed 'has child node' to 'yes'--------------------      
  #--------------------------------------------------------
  #ON EDIT
  def group_changed(self,r):

    if r['node_title']  != 'Sales Person' and r['is_group'] == 'Yes':
      field = 'default_'+r['node_title'].lower().replace(' ','_')
      res = sql("select value from `tabSingles` where field = '%s' and value = '%s'"%(field,r['nm']))
      if res:
        msgprint("'%s' record is set as default record in Global Defaults.'Has Child Node' field cannot be changed to 'Yes' as only leaf nodes are allowed in transaction."%(r['nm']))
        return 'true'
      
    return 'false'
  #-------------------validation - record is already exist--------------------------------
  #ON CREATE
  def trash_rcd(self,r):
    res = sql("select name from `tab%s` where name = '%s' and docstatus = 2"%(r['node_title'],r['nm']))
    if res:
      msgprint("'%s' record is trashed. To untrash please go to Setup & click on Trash."%(r['nm']))
      return 'true'

    return 'false'

  #----------------------------------------------------------------  
  #ON CREATE
  def duplicate_rcd(self,r):
    res = sql("select name from `tab%s` where name = '%s' and docstatus != 2"%(r['node_title'],r['nm']))
    if res:
      msgprint("'%s' record is already exist."%(r['nm']))
      return 'true'
    return 'false'      