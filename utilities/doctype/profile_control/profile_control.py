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

from webnotes.utils import cstr
from webnotes.model import db_exists
from webnotes.model.doc import Document
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	


class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d,dl
    self.last_profile = None
  
  def get_role_permission(self,role):
    perm = sql("select distinct t1.`parent`, t1.`read`, t1.`write`, t1.`create`, t1.`submit`,t1.`cancel`,t1.`amend` from `tabDocPerm` t1, `tabDocType` t2 where t1.`role` ='%s' and t1.docstatus !=2 and t1.permlevel = 0 and t1.`read` = 1 and t2.module != 'Recycle Bin' and t1.parent=t2.name "%role)
    return perm or ''

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
      
