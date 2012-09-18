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
sql = webnotes.conn.sql

class DocType:
  def __init__(self, d, dl):
    self.doc, self.doclist = d, dl

  # on update
  # ---------- 
  def on_update(self):
    self.update_primary_shipping_address()
    self.get_customer_details()

  # set is_primary_address for other shipping addresses belonging to same customer
  # -------------------------------------------------------------------------------
  def update_primary_shipping_address(self):
    if self.doc.is_primary_address == 'Yes':
      sql("update `tabShipping Address` set is_primary_address = 'No' where customer = %s and is_primary_address = 'Yes' and name != %s",(self.doc.customer, self.doc.name))

  # Get Customer Details
  # ---------------------
  def get_customer_details(self):
    det = sql("select customer_name, address from tabCustomer where name = '%s'" % (self.doc.customer))
    self.doc.customer_name = det and det[0][0] or ''
    self.doc.customer_address = det and det[0][1] or ''
