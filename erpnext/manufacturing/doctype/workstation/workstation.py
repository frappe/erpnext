# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist

	


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  def update_bom_operation(self):
      bom_list = webnotes.conn.sql(" select DISTINCT parent from `tabBOM Operation` where workstation = '%s'" % self.doc.name)
      for bom_no in bom_list:
        webnotes.conn.sql("update `tabBOM Operation` set hour_rate = '%s' where parent = '%s' and workstation = '%s'"%( self.doc.hour_rate, bom_no[0], self.doc.name))
  
  def on_update(self):
    webnotes.conn.set(self.doc, 'overhead', flt(self.doc.hour_rate_electricity) + flt(self.doc.hour_rate_consumable) + flt(self.doc.hour_rate_rent))
    webnotes.conn.set(self.doc, 'hour_rate', flt(self.doc.hour_rate_labour) + flt(self.doc.overhead))
    self.update_bom_operation()