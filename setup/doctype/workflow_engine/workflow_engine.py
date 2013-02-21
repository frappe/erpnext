# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.model import db_exists
from webnotes.model.bean import getlist, copy_doclist
from webnotes.model.code import get_obj
from webnotes import form, msgprint

sql = webnotes.conn.sql
	


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