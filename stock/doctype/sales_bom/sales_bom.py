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
  def __init__(self,d,dl):
    self.doc, self.doclist = d,dl

  def autoname(self):
    self.doc.name = make_autoname(self.doc.new_item_code)

  
  # Get Ref Rates
  # --------------
  def get_rates(self):
    for d in getlist(self.doclist, "sales_bom_items"):
      r = sql("select ref_rate from `tabRef Rate Detail` where price_list_name=%s and parent=%s and ref_currency = %s", (self.doc.price_list, d.item_code, self.doc.currency))
      d.rate = r and flt(r[0][0]) or 0.00


  # Get Item Details
  # -----------------
  def get_item_details(self, name):
    det = sql("select description, stock_uom from `tabItem` where name = '%s' " % cstr(name))
    rate = sql("select ref_rate from `tabRef Rate Detail` where price_list_name = %s and parent = %s and ref_currency = %s", (self.doc.price_list, name, self.doc.currency))
    return {'description' : det and det[0][0] or '', 'uom': det and det[0][1] or '', 'rate': rate and flt(rate[0][0]) or 0.00}


  def get_main_item(self):
    is_main_item = []
    for d in getlist(self.doclist,'sales_bom_items'):
      if d.is_main_item == 'Yes':
        is_main_item.append(d.item_code)
      # Check that Sales Bom Item cannot be child of Sales Bom.
      if sql("select name from `tabSales BOM` where name = '%s' " % d.item_code):
        msgprint("Sales Bom Item " + d.item_code +" cannot be child item.")
        raise Exception
      # Check if is_main_item is modified once saved
      if not self.doc.fields.get('__islocal') and d.is_main_item == "Yes" and cstr(d.item_code) != cstr(self.doc.name)[:-3] :
        msgprint("Modifying the main item is not allowed.")
        raise Exception
    if len(is_main_item) > 1:
      msgprint('Main item cannot be more than one.')
      raise Exception , " Validation Error."
    if len(is_main_item) == 0:
      msgprint("At least one item should be main item.")
      raise Exception , " Validation Error."
    return is_main_item[0]


  # Make Item
  # ---------
  def create_new_item(self):
    i = Document("Item")
    
    i.item_code = self.doc.new_item_code
    i.item_name = self.doc.new_item_name
    i.name = i.item_code
    i.is_sales_item = 'Yes'
    i.is_stock_item = 'No'
    i.save(1)

# This function is deprecated as we will see only pricelist which is selected 
#  def get_price_lists(self):
#    return [i[0] for i in sql("select name from `tabPrice List` where docstatus != 2")]

  # Update Rate
  # -----------
  
  def update_ref_rate(self, i):
    ref_rate,count, p, currency  =  0,0, self.doc.price_list, self.doc.currency
    if not cstr(self.doc.price_list):
      msgprint("Please enter Price List.")
      raise Exception
    if not cstr(self.doc.currency):
      msgprint("Please enter Currency.")
      raise Exception
    for d in getlist(self.doclist, "sales_bom_items"):
      item_rate = sql("select ref_rate,ref_currency from `tabRef Rate Detail` where price_list_name=%s and parent=%s", (p, d.item_code))      
      if not item_rate:
        msgprint("Item %s does not have a rate for Price List %s. Did not update rates for this Price List" % (d.item_code, p))
        raise Exception
      # if count == 0 : currency = cstr(item_rate[0][1])
      if not cstr(currency) == cstr(item_rate[0][1]):
        msgprint("Item %s currency %s does not match with other items currency i.e. %s " %(d.item_code,item_rate[0][1],currency))
        raise Exception
      count += 1
      ref_rate += (flt(d.qty) * flt(item_rate[0][0]))
      
    pld = addchild(i,"ref_rate_details", "Ref Rate Detail")
    pld.price_list_name = p
    pld.ref_rate = flt(ref_rate)
    pld.ref_currency = currency
    pld.save()

      
  # Update Items
  # ------------
  def update_item(self):
    i = Document("Item", self.doc.new_item_code)
    
    # update fields
    i.brand = self.doc.new_item_brand
    i.stock_uom = self.doc.stock_uom 
    i.item_group = self.doc.item_group
	
    # clear old rates
    sql("delete from `tabRef Rate Detail` where parent=%s", i.name)
    
    # update rates
    new_rates = {}
    # pl_list = self.get_price_lists()
    #for p in self.get_price_lists():
    self.update_ref_rate(i)

    # update description and item name
    n1, n2 = [], []
    for d in getlist(self.doclist, "sales_bom_items"):
      n, desc = sql("select item_name, description from tabItem where name=%s", d.item_code)[0]
      n1.append(n)
      n2.append(desc)
    
    self.doc.new_item_name = (' ').join(n1)
    self.doc.description = ("\n" + "\n").join(n2)

    i.item_name = self.doc.new_item_name
    i.description = self.doc.description

    # set default as 'No' or 0 in Item Master  as per TIC/3456
    i.is_sample_item = 'No'
    i.is_asset_item = 'No'
    i.is_purchase_item = 'No'
    i.is_manufactured_item = 'No'
    i.is_sub_contracted_item = 'No'
    i.is_service_item = 'No'
    i.inspection_required = 'No'
    i.has_serial_no = 'No'
    i.lead_time_days = flt(0)
    i.save()
    msgprint("Items updated successfully.")


  def validate(self):
    # check for duplicate
    self.check_duplicate()
    item_code = self.get_main_item()
    if not self.doc.new_item_code:
      self.doc.new_item_code = make_autoname(item_code +'.###')

 
  def on_update(self):
    # if no item code, create new item code
    if not sql("select name from tabItem where name=%s", self.doc.new_item_code):
      self.create_new_item()
    self.update_item()


  def check_duplicate(self, finder=0):
    il = getlist(self.doclist, "sales_bom_items")
    if not il:
      msgprint("Add atleast one item")
      return
    
    # get all Sales BOM that have the first item  
    sbl = sql("select distinct parent from `tabSales BOM Detail` where item_code=%s", il[0].item_code)
    
    # check all siblings
    sub_items = [[d.item_code, flt(d.qty)] for d in il]
    
    for s in sbl:
      if not cstr(s[0]) == cstr(self.doc.name) :
        t = sql("select item_code, qty from `tabSales BOM Detail` where parent=%s", s[0])
        t = [[d[0], flt(d[1])] for d in t]
  
        if self.has_same_items(sub_items, t):
          msgprint("%s has the same Sales BOM details" % s[0])
          raise Exception
    if finder:
      msgprint("There is no Sales BOM present with the following Combination.")


  def has_same_items(self, l1, l2):
    if len(l1)!=len(l2): return 0
    for l in l2:
      if l not in l1:
        return 0
    for l in l1:
      if l not in l2:
        return 0
    return 1