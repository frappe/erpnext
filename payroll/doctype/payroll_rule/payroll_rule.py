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
  
  #----------------------------------------------------
  # list of master whose module is payroll & isnot table
  def get_masters(self):
    master1 = sql("select name from `tabDocType` where module = 'Payroll' and (istable = 0 or istable is null)")
    ret =''
    if master1:
      for i in master1:
        ret += "\n" + i[0]
    return ret
    

  #---------------------------------------------------- 
  #list of all fields for which conditions can be set
  def maindoc_field(self, select_form):
    field_list=[]
    
    
    field_info = sql("select label,fieldtype,options,fieldname from `tabDocField` where parent='%s' and fieldtype not in('Section Break','Column Break','Text','Small Text','Text Editor', 'Time', 'Check', 'Button','Code','HTML','Image','Blob','Password')"%select_form)
    
    for f in field_info:
      sl=[]
      for x in f:
        sl.append(x)
      field_list.append(sl)
    ret = ''
    
    #=====================================================  
    
    for fi in field_list:
      if fi[1] !='Select' or fi[1] !='Link' or fi[1] !='Table':
        ret += "\n" + cstr(select_form) + ':' + fi[0]
      elif fi[1] =='Select':
        op = fi[2].split(':')
        if op[0] != 'link':
          ret += "\n" + cstr(select_form) + ':' +fi[0]
        #========  
        # linked doctype field list
    
    #=====================================================  
    
    for fi in field_list:    
      if fi[1] == 'Link':
        flist=sql("select label from tabDocField where parent='%s' and fieldtype in ('Data', 'Int', 'Select','Currency','Float','Link')"%fi[2])
        for f in flist:
          ret += "\n" + fi[0] + ':' +f[0]
      elif fi[1] == 'Select':
        op = fi[2].split(':')
        if op[0] == 'link':
          flist=sql("select label from tabDocField where parent='%s' and fieldtype in ('Data', 'Select', 'Int','Currency','Float','Link')"%op[1])
          for f in flist:
            ret += "\n" + fi[0] + ':' +f[0]

    return ret


  #----------------------------------------------------  
  # function for finding fieldname,datatype of mentioned label
  def field_info(self,label,parent):
    field_name=sql("select fieldname from tabDocField where parent='%s' and label='%s'" %(parent,label))[0][0]
    if field_name: 
      datatype=sql("select fieldtype from `tabDocField` where fieldname='%s' and parent='%s'" %(field_name,parent))[0][0]
      ret={'fieldnm':field_name,'datatype':datatype}
    
    return ret
  
  #----------------------------------------------------
  def compare_string(self,first,second,op):

    if op=='Equals':
      if first.lower()==second.lower():
        return 'true'
      else:
        return 'false'
    elif op=='Not Equals':
      if first.lower()!=second.lower():
        return 'true'
      else:
        return 'false'
    elif op=='Greater than':
      if first.lower()>second.lower():
        return 'true'
      else:
        return 'false'
    elif op=='Greater than or Equals':
      if first.lower()>=second.lower():
        return 'true'
      else:
        return 'false'
    elif op=='Less than':
      if first.lower()<second.lower():
        return 'true'
      else:
        return 'false'
    elif op=='Less than or Equals':
      if first.lower()<=second.lower():
        return 'true'
      else:
        return 'false'
 
  
  #----------------------------------------------------
  #evalute operator
  def eval_operator(self,op):
    op_sign =''
    if op=='Equals':
      op_sign='=='
    elif op=='Not Equals':
      op_sign='!='
    elif op=='Greater than':
      op_sign='>'
    elif op=='Greater than or Equals':
      op_sign='>='
    elif op=='Less than':
      op_sign='<'
    elif op=='Less than or Equals':
      op_sign='<='
    
    return op_sign
  
  #----------------------------------------------------  
  #evaluation condition
  def eval_condition(self,field_dict,form_val,value,operator):
    if field_dict['datatype']=='Data' or field_dict['datatype']=='Select' or field_dict['datatype'] =='Link':
      
      if self.compare_string(cstr(form_val),cstr(value),operator)=='false':
        cond_hold='No'
      else:
        cond_hold='Yes'
    else:
      op_sign = self.eval_operator(operator)  
      chk_cond=str(form_val) + str(op_sign) + str(value)
      errprint(chk_cond)
      if eval(chk_cond):
        cond_hold='Yes'
      else:
        cond_hold='No'
   
    return cond_hold
  
  #----------------------------------------------------
  # fetching the value from the form
  def find_value(self,fld_nm,tab_nm,rec_nm,child=0):
    if child == 0:
      form_val=sql("select %s from `tab%s` where name='%s'"%(fld_nm,tab_nm,rec_nm))
    
    elif child == 1:
      form_val=sql("select %s from `tab%s` where parent='%s'"%(fld_nm,tab_nm,rec_nm))
    
    return form_val and form_val[0][0]
  
  #----------------------------------------------------
  # checking with main doctype  
  def chk_from_main_dt(self,master,label1,value,operator,form_obj):
    cond_hold = ''
    field_dict = self.field_info(label1,master) #getting fieldname info
    form_val=self.find_value(field_dict['fieldnm'],master,form_obj.doc.name) # find value
   
    if form_val :
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    elif not form_val and field_dict['datatype'] =='Currency' or field_dict['datatype'] =='Float' or field_dict['datatype'] =='Int':
      
      form_val = 0.0
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    return cond_hold

  #----------------------------------------------------  
  #checking with child doctype
  def chk_from_child_dt(self,first_label,second_label,value,operator,form_obj):
    cond_hold = ''
    field_dict = self.field_info(second_label,first_label)
    form_val=self.find_value(field_dict['fieldnm'],first_label,form_obj.doc.name,1) #fetching the value in current form from a table
    if form_val or form_val==0:
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    
    return cond_hold

  #----------------------------------------------------
  # if checking is with any linked doctype means first_label field from the doctype for which rule is given and second_label field from the doctype with which first_label is linked  
  
  def chk_from_link_dt(self,master,first_label,second_label,form_obj,value,operator):
    cond_hold=''
    field_list=[]
    field_dict_first = self.field_info(first_label,master)
    field_info = sql("select label,fieldtype,options,fieldname from `tabDocField` where parent='%s' and fieldtype not in('Section Break','Column Break','Text','Small Text','Text Editor', 'Time', 'Check', 'Button','Code','HTML','Image','Blob','Password')"%master)
    for f in field_info:
      sl=[]
      for x in f:
        sl.append(x)
      field_list.append(sl)
    for x in field_list:
      if x[3] == field_dict_first['fieldnm']:
        linked_to = x[2]
    
    lt = linked_to.split(':')
    
    #=================================================
    if lt[0] == 'link':
      field_dict_second = self.field_info(second_label,lt[1])
      link_val=sql("select %s from `tab%s` where name='%s'"%(field_dict_first['fieldnm'],master,form_obj.doc.name))
      if link_val and link_val[0][0]:
        form_val = self.find_value(field_dict_second['fieldnm'],lt[1],link_val[0][0])
        if form_val :
          cond_hold = self.eval_condition(field_dict_second,form_val,value,operator)
      
    else:
      field_dict_second = self.field_info(second_label,lt[0])
      link_val=sql("select %s from `tab%s` where name='%s'"%(field_dict_first['fieldnm'],master,form_obj.doc.name))
      if link_val and link_val[0][0]:
        form_val = self.find_value(field_dict_second['fieldnm'],lt[0],link_val[0][0])
        if form_val :
          cond_hold = self.eval_condition(field_dict_second,form_val,value,operator)
    
    return cond_hold

  #----------------------------------------------------
  def evalute_rule(self,form_obj):
    
    all_cond_hold='Yes'
    for d in getlist(self.doclist,'condition_details'):
      master = d.rule_master
      label = d.rule_field.split(':')  #break up checking condition
      
      #findout the value with which condition will be checked
      if d.value:
        chk_with_value = d.value
        
      
      # label[0] is doctype name for which rule is given, label[1] field name of that doctype
      if label[0] == master:
        cond_hold = self.chk_from_main_dt(master,label[1],chk_with_value,d.operator,form_obj) 
        if cond_hold =='No':
          all_cond_hold = 'No'
          break
        elif cond_hold =='Yes':
          all_cond_hold ='Yes'
          
      #=====================================================   
      # if checking is with any linked doctype means label[0] field from the doctype for which rule is given and label[1] field from the doctype with which label[0] is linked
      else:
        cond_hold=self.chk_from_link_dt(master,label[0],label[1],form_obj,chk_with_value,d.operator)
        if cond_hold =='No':
          if d.exception == 'Yes':
              msgprint(d.message)
              raise Exception
          elif d.exception=='No' or d.exception=='':
              msgprint(d.message)
          all_cond_hold = 'No'
          break
        elif cond_hold =='Yes':
          all_cond_hold ='Yes'
   
    return all_cond_hold
  
  #----------------------------------------------------
  #list of values of label & fieldname of selected master    
  def get_values(self):
    op = self.doc.select_field2.split(':')
    
    if op[0] == self.doc.master2:
      field_info = sql("select label,fieldname from `tabDocField` where parent= '%s' AND label = '%s'" %(self.doc.select_master2,op[1]))
      
    else:
      field_info = sql("select label,fieldname from `tabDocField` where parent= '%s' AND label = '%s'" %(op[0],op[1]))
      
    comp = sql("SELECT DISTINCT %s FROM `tab%s`" %(field_info[0][1],op[0]))
    
    res = ''
    for i in comp:
      res +=  "\n" + str(i[0])
    
    return cstr(res)

  #----------------------------------------------------  
  #add_details function add records in condition detail table     
  def add_details(self):
    
    if((self.doc.select_master)  and (self.doc.select_field)):
      if((self.doc.right_operand=='Automatic') and (self.doc.select_value=='')):
        msgprint("Please select value")
      else:
        ch = addchild(self.doc,'condition_details','Condition Detail',0, self.doclist)
        ch.rule_master = self.doc.select_master
        ch.rule_field = self.doc.select_field
        ch.operator = 'Equals'
        ch.value = self.doc.select_value
        ch.save()
    else:
      msgprint("Please select form, select field")