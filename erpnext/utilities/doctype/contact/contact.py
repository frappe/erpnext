# Please edit this list and import only required elements
import webnotes

from webnotes.model.doc import Document
from webnotes import session, form, msgprint, errprint

sql = webnotes.conn.sql
  
# -----------------------------------------------------------------------------------------

class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  def autoname(self):
    if self.doc.customer:
      self.doc.name = self.doc.first_name + (self.doc.last_name and ' ' + self.doc.last_name or '') + '-' + self.doc.customer
    elif self.doc.supplier:
      self.doc.name = self.doc.first_name + (self.doc.last_name and ' ' + self.doc.last_name or '') + '-' + self.doc.supplier
    elif self.doc.sales_partner:
      self.doc.name = self.doc.first_name + (self.doc.last_name and ' ' + self.doc.last_name or '') + '-' + self.doc.sales_partner  
    
    # filter out bad characters in name
    #self.doc.name = self.doc.name.replace('&','and').replace('.','').replace("'",'').replace('"','').replace(',','')      

#----------------------
# Call to Validate
#----------------------
  def validate(self):
    self.validate_primary_contact()

#----------------------
# Validate that there can only be one primary contact for particular customer, supplier
#----------------------
  def validate_primary_contact(self):
    if self.doc.is_primary_contact == 1:
      if self.doc.customer:
        sql("update tabContact set is_primary_contact=0 where customer = '%s'" % (self.doc.customer))
      elif self.doc.supplier:
        sql("update tabContact set is_primary_contact=0 where supplier = '%s'" % (self.doc.supplier))  
      elif self.doc.sales_partner:
        sql("update tabContact set is_primary_contact=0 where sales_partner = '%s'" % (self.doc.sales_partner))  
