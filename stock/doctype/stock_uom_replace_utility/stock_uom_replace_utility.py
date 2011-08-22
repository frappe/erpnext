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
  def __init__(self, d, dl=[]):
    self.doc, self.doclist = d,dl

  def get_stock_uom(self, item_code):
    return {'current_stock_uom': cstr(get_value('Item', item_code, 'stock_uom'))}
  
  def validate_mandatory(self):
    if not cstr(self.doc.item_code):
      msgprint("Please Enter an Item.")
      raise Exception

    if not cstr(self.doc.current_stock_uom):
      msgprint("There is no Current Stock UOM for Item Code" + cstr(self.doc.item_code))
      raise Exception
    
    if not cstr(self.doc.new_stock_uom):
      msgprint("Please Enter New Stock UOM.")
      raise Exception

    if cstr(self.doc.current_stock_uom) == cstr(self.doc.new_stock_uom):
      msgprint("Current Stock UOM and Stock UOM are same.")
      raise Exception 
  
    # check conversion factor
    if not flt(self.doc.conversion_factor):
      msgprint("Please Enter Conversion Factor.")
      raise Exception
    
    stock_uom = sql("select stock_uom from `tabItem` where name = '%s'" % self.doc.item_code)
    stock_uom = stock_uom and stock_uom[0][0]
    if cstr(self.doc.new_stock_uom) == cstr(stock_uom):
      msgprint("Item Master is already updated with New Stock UOM " + cstr(self.doc.new_stock_uom))
      raise Exception
      
  def update_item_master(self):
    # update stock uom in item master
    sql("update `tabItem` set stock_uom = '%s' where name = '%s' " % (self.doc.new_stock_uom, self.doc.item_code))
    
    # acknowledge user
    msgprint("New Stock UOM : " + cstr(self.doc.new_stock_uom) + " updated in Item : " + cstr(self.doc.item_code))
    
  def update_bin(self):
    # update bin
    if flt(self.doc.conversion_factor) != flt(1):
      sql("update `tabBin` set stock_uom = '%s' , indented_qty = ifnull(indented_qty,0) * %s, ordered_qty = ifnull(ordered_qty,0) * %s, reserved_qty = ifnull(reserved_qty,0) * %s, planned_qty = ifnull(planned_qty,0) * %s, projected_qty = actual_qty + ordered_qty + indented_qty + planned_qty - reserved_qty  where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.conversion_factor, self.doc.item_code) )
    else:
      sql("update `tabBin` set stock_uom = '%s' where item_code = '%s'" % (self.doc.new_stock_uom, self.doc.item_code) )

    # acknowledge user
    msgprint(" All Bin's Updated Successfully.")
      
  def update_stock_ledger_entry(self):
    # update stock ledger entry
    if flt(self.doc.conversion_factor) != flt(1):
      sql("update `tabStock Ledger Entry` set stock_uom = '%s', actual_qty = ifnull(actual_qty,0) * '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.conversion_factor, self.doc.item_code))
    else:
      sql("update `tabStock Ledger Entry` set stock_uom = '%s' where item_code = '%s' " % (self.doc.new_stock_uom, self.doc.item_code))
    
    # acknowledge user
    msgprint("Stock Ledger Entries Updated Successfully.")
    
    # update item valuation
    if flt(self.doc.conversion_factor) != flt(1):
      wh = sql("select name from `tabWarehouse`")
      for w in wh:
        bin = sql("select name from `tabBin` where item_code = '%s' and warehouse = '%s'" % (self.doc.item_code, w[0])) 
        if bin and bin[0][0]:
          get_obj("Bin", bin[0][0]).update_item_valuation(sle_id = '', posting_date = '', posting_time = '')

    # acknowledge user
    msgprint("Item Valuation Updated Successfully.")

  # Update Stock UOM              
  def update_stock_uom(self):
    # validate mandatory
    self.validate_mandatory()
    
    # update item master
    self.update_item_master()
    
    # update stock ledger entry
    self.update_stock_ledger_entry()
    
    # update bin
    self.update_bin()