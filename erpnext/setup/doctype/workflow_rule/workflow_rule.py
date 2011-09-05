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
    
    self.field_list=[]
    field_info = sql("select label,fieldtype,options,fieldname from `tabDocField` where parent='%s' and fieldtype not in('Section Break','Column Break','Text','Small Text','Text Editor', 'Time', 'Check', 'Button','Code','HTML','Image','Blob','Password')"%self.doc.select_form)
    for f in field_info:
      sl=[]
      for x in f:
        sl.append(x)
      self.field_list.append(sl)
 
#list of labels
  def field_label_list(self):
    label= ''
    for fi in self.field_list:
      if fi[1] !='Table':
        label += "\n" + fi[0]
    
    return label
  
 
  def compare_field(self):
    ret1=''
    for fi in self.field_list:
      if fi[1] =='Table':
        flist=sql("select label from tabDocField where parent='%s' and fieldtype in ('Data', 'Select', 'Int','Currency','Float','Link')"%fi[2])
        for x in flist:
          ret1 += "\n" + fi[2] + ':' + x[0]
      else:
        ret1 += "\n" + cstr(self.doc.select_form) + ':' + fi[0]
   
    return cstr(ret1)
  
#list of all fields for which conditions can be set
  def maindoc_field(self):
    ret = ''
    for fi in self.field_list:
      if fi[1] !='Select' or fi[1] !='Link' or fi[1] !='Table':
        ret += "\n" + cstr(self.doc.select_form) + ':' + fi[0]
      elif fi[1] =='Select':
        op = fi[2].split(':')
        if op[0] != 'link':
          ret += "\n" + cstr(self.doc.select_form) + ':' +fi[0]

    #child table field list
    for fi in self.field_list:    
      if fi[1] == 'Table':
        flist=sql("select label from tabDocField where parent='%s' and fieldtype in ('Data', 'Select', 'Int','Currency','Float','Link')"%fi[2])
        for x in flist:
          ret += "\n" + fi[2] + ':' + x[0]
    
    # linked doctype field list
    for fi in self.field_list:    
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

    return cstr(ret)
    
  #table name of the selected doctype
  def child_doc(self):
    lst=[]
    for fi in self.field_list:    
      if fi[1] == 'Table':
        lst.append(fi[2])
    
    return lst
  
  # function for finding fieldname,datatype of mentioned label
  def field_info(self,label,parent):
    field_name=sql("select fieldname from tabDocField where parent='%s' and label='%s'" %(parent,label))[0][0]
    if field_name: 
      datatype=sql("select fieldtype from `tabDocField` where fieldname='%s' and parent='%s'" %(field_name,parent))[0][0]
      ret={'fieldnm':field_name,'datatype':datatype}
    
    return ret
  
  def compare_string(self,first,second):
    if first.lower()==second.lower():
      return 'true'
    else:
      return 'false'
  
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
    
#evaluation condition
  def eval_condition(self,field_dict,form_val,value,operator):
  
    if field_dict['datatype']=='Data' or field_dict['datatype']=='Select' or field_dict['datatype'] =='Link':
      #msgprint("not eval")
      if self.compare_string(cstr(form_val),cstr(value))=='false':
        cond_hold='No'
      else:
        cond_hold='Yes'
    else:
      #msgprint("eval")
      op_sign = self.eval_operator(operator)
      chk_cond=str(form_val) + str(op_sign) + str(value)
      #msgprint(chk_cond)
      if eval(chk_cond):
        cond_hold='Yes'
      else:
        cond_hold='No'
    #msgprint(cond_hold)
    return cond_hold
  
  
# fetching the value from the form
  def find_value(self,fld_nm,tab_nm,rec_nm,child=0):
    if child == 0:
      form_val=sql("select %s from `tab%s` where name='%s'"%(fld_nm,tab_nm,rec_nm))
    
    elif child == 1:
      form_val=sql("select %s from `tab%s` where parent='%s'"%(fld_nm,tab_nm,rec_nm))
    
    return form_val and form_val[0][0]
  
# if the comparing value is not entered manually but fetching from some other field
  def compare_field_not_manual(self,comparing_field):
    chk_with_value =''
    temp_val = comparing_field.split(':')
    if temp_val[0] == self.doc.select_form:
      field_cf = self.field_info(temp_val[1],self.doc.select_form) 
      val_cf=self.find_value(field_cf['fieldnm'],self.doc.select_form,form_obj.doc.name)     
      chk_with_value = val_cf
    elif temp_val[0] in child_list:
      field_cf = self.field_info(second_label,first_label)
      val_cf=self.find_value(field_cf['fieldnm'],first_label,form_obj.doc.name,1) 
      chk_with_value = val_cf
    
    return chk_with_value
# checking with main doctype  
  def chk_from_main_dt(self,label1,value,operator,form_obj):
    cond_hold = ''
    field_dict = self.field_info(label1,self.doc.select_form) #getting fieldname info
    form_val=self.find_value(field_dict['fieldnm'],self.doc.select_form,form_obj.doc.name) # find value
    #msgprint(cstr(form_val))
    if form_val :
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    elif not form_val and field_dict['datatype'] =='Currency' or field_dict['datatype'] =='Float' or field_dict['datatype'] =='Int':
      #msgprint("1") 
      form_val = 0.0
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    return cond_hold

#checking with child doctype
  def chk_from_child_dt(self,first_label,second_label,value,operator,form_obj):
    cond_hold = ''
    field_dict = self.field_info(second_label,first_label)
    form_val=self.find_value(field_dict['fieldnm'],first_label,form_obj.doc.name,1) #fetching the value in current form from a table
    if form_val or form_val==0:
      cond_hold = self.eval_condition(field_dict,form_val,value,operator)
    
    return cond_hold

  
# if checking is with any linked doctype means first_label field from the doctype for which rule is given and second_label field from the doctype with which first_label is linked  
  def chk_from_link_dt(self,first_label,second_label,form_obj,value,operator):
    cond_hold=''
    field_dict_first = self.field_info(first_label,self.doc.select_form)
    for x in self.field_list:
      if x[3] == field_dict_first['fieldnm']:
        linked_to = x[2]
    
    lt = linked_to.split(':')
    if lt[0] == 'link':
      field_dict_second = self.field_info(second_label,lt[1])
      link_val=sql("select %s from `tab%s` where name='%s'"%(field_dict_first['fieldnm'],self.doc.select_form,form_obj.doc.name))
      if link_val and link_val[0][0]:
        form_val = self.find_value(field_dict_second['fieldnm'],lt[1],link_val[0][0])
        if form_val :
          cond_hold = self.eval_condition(field_dict_second,form_val,value,operator)
      
    else:
      field_dict_second = self.field_info(second_label,lt[0])
      link_val=sql("select %s from `tab%s` where name='%s'"%(field_dict_first['fieldnm'],self.doc.select_form,form_obj.doc.name))
      if link_val and link_val[0][0]:
        form_val = self.find_value(field_dict_second['fieldnm'],lt[0],link_val[0][0])
        if form_val :
          cond_hold = self.eval_condition(field_dict_second,form_val,value,operator)
    
    return cond_hold

  
  def evalute_rule(self,form_obj):
    #msgprint(form_obj.doc.name)
    child_list = self.child_doc()
    all_cond_hold=''
    for d in getlist(self.doclist,'workflow_rule_details'):
      label = d.rule_field.split(':')  #break up checking condition
      
      #findout the value with which condition will be checked
      if d.value:
        chk_with_value = d.value
      elif d.comparing_field:
        chk_with_value = self.compare_field_not_manual(d.comparing_field)  
      
      #msgprint(label)
      # label[0] is doctype name for which rule is given, label[1] field name of that doctype
      if label[0] == self.doc.select_form:
        cond_hold = self.chk_from_main_dt(label[1],chk_with_value,d.operator,form_obj) 
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
      	
      #label[0] is child doctype name , label[1] is child doctype field name
      elif label[0] in child_list:
        cond_hold = self.chk_from_child_dt(label[0],label[1],chk_with_value,d.operator,form_obj) 
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
       
      # if checking is with any linked doctype means label[0] field from the doctype for which rule is given and label[1] field from the doctype with which label[0] is linked
      else:
        cond_hold=self.chk_from_link_dt(label[0],label[1],form_obj,chk_with_value,d.operator)
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
