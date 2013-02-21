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

from webnotes.utils import flt
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  def update_bom_operation(self):
      bom_list = sql(" select DISTINCT parent from `tabBOM Operation` where workstation = '%s'" % self.doc.name)
      for bom_no in bom_list:
        sql("update `tabBOM Operation` set hour_rate = '%s' where parent = '%s' and workstation = '%s'"%( self.doc.hour_rate, bom_no[0], self.doc.name))
  
  def on_update(self):
    webnotes.conn.set(self.doc, 'overhead', flt(self.doc.hour_rate_electricity) + flt(self.doc.hour_rate_consumable) + flt(self.doc.hour_rate_rent))
    webnotes.conn.set(self.doc, 'hour_rate', flt(self.doc.hour_rate_labour) + flt(self.doc.overhead))
    self.update_bom_operation()