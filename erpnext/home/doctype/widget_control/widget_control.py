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

import webnotes

from webnotes.utils import nowdate
from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint 

sql = webnotes.conn.sql

try: import json
except: import simplejson as json

# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
      
  def add_comment(self,args):
    import time
    args = eval(args)
    if(args['comment']):
      cmt = Document('Comment Widget Record')
      for arg in args:
        cmt.fields[arg] = args[arg]
      cmt.comment_date = nowdate()
      cmt.comment_time = time.strftime('%H:%M')
      cmt.save(1)
	      
    else:
      raise Exception
        
  def remove_comment(self, args):
    args = json.loads(args)
    sql("delete from `tabComment Widget Record` where name=%s",args['id'])
