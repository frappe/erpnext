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
