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
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  def validate(self):
    import string
  
    if not (self.doc.address_line1)  and not (self.doc.address_line2) and not (self.doc.city) and not (self.doc.state) and not (self.doc.country) and not (self.doc.pincode):
      return "Please enter address"
      
    else:
      address =["address_line1", "address_line2", "city", "state", "country", "pincode"]
      comp_address=''
      for d in address:
        if self.doc.fields[d]:
          comp_address += self.doc.fields[d] + "\n"
      self.doc.address = comp_address
    
  def get_contacts(self,nm):
    if nm:
      contact_details =webnotes.conn.convert_to_lists(sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where sales_partner = '%s'"%nm))
      return contact_details
    else:
      return ''