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
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  # Autoname
  def autoname(self):
    p = self.doc.fiscal_year
    self.doc.name = make_autoname('PRO/' + self.doc.fiscal_year[2:5]+self.doc.fiscal_year[7:9] + '/.######')

  def get_item_detail(self, production_item):
    item = sql("select description, stock_uom, default_bom from `tabItem` where (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now()) and name = %s", production_item, as_dict = 1 )
    ret = {
            'description' : item and item[0]['description'] or '',
            'stock_uom'   : item and item[0]['stock_uom'] or '',
            'default_bom' : item and item[0]['default_bom'] or ''
    }
    return ret
    
  def validate(self):
    if not self.doc.production_item :
      msgprint("Please enter Production Item")
      raise Exception
    if self.doc.production_item :
      item_detail = sql("select docstatus from `tabItem` where name = '%s'" % self.doc.production_item, as_dict = 1)
      if not item_detail:
        msgprint("Item '%s' do not exist in the system." % cstr(self.doc.production_item))
        raise Exception
      if item_detail[0]['docstatus'] == 2:
        msgprint("Item '%s' is Trashed Item ."% self.doc.production_item)
        raise Exception
    if self.doc.bom_no:
      bom_detail = sql("select item, is_active, docstatus from `tabBill Of Materials` where name = '%s'" % self.doc.bom_no, as_dict =1)
      if not bom_detail:
        msgprint("BOM No '%s' do not exist in the system." % cstr(self.doc.bom_no))
        raise Exception
      if cstr(bom_detail[0]['item']) != cstr(self.doc.production_item):
        msgprint("The Item '%s' in BOM := '%s' do not match with Produciton Item '%s'." % (cstr(bom_detail[0]['item']), cstr(self.doc.bom_no), cstr(self.doc.production_item)))
        raise Exception
      if cstr(bom_detail[0]['is_active']) != 'Yes':
        msgprint("BOM := '%s' is not Active BOM." % self.doc.bom_no)
        raise Exception
      if flt(bom_detail[0]['docstatus']) != 1:
        msgprint("BOM := '%s' is not Submitted BOM." % self.doc.bom_no)
        raise Exception
  
  def update_status(self, status):
    # Set Status
    if status == 'Stopped':
      set(self.doc, 'status', cstr(status))
    else:
      if flt(self.doc.qty) == flt(self.doc.produced_qty):
        set(self.doc, 'status', 'Completed')
      if flt(self.doc.qty) > flt(self.doc.produced_qty):
        set(self.doc, 'status', 'In Process')
      if flt(self.doc.produced_qty) == 0:
        set(self.doc, 'status', 'Submitted')

    # Update Planned Qty of Production Item
    qty = (flt(self.doc.qty) - flt(self.doc.produced_qty)) * ((status == 'Stopped') and -1 or 1)
    get_obj('Warehouse', self.doc.fg_warehouse).update_bin(0, 0, 0, 0, flt(qty), self.doc.production_item, now())
    
    # Acknowledge user
    msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s and status has been updated as %s." % (cstr(status), cstr(self.doc.status)))

  def on_submit(self):
    # Set Status AS "Submitted"
    set(self.doc,'status', 'Submitted')

    # increase Planned Qty of Prooduction Item by Qty
    get_obj('Warehouse', self.doc.fg_warehouse).update_bin(0, 0, 0, 0,flt(self.doc.qty), self.doc.production_item, now())


  def on_cancel(self):
    # Stock Entries Against this Production Order
    st = sql("select name from `tabStock Entry` where production_order = '%s' and docstatus = 1" % cstr(self.doc.name))
    if st and st[0][0]:
      msgprint("Stock Entry "+ cstr(st[0][0]) + " has already been submitted.")
      raise Exception

    # Set Status AS "Submitted"
    set(self.doc,'status', 'Cancelled')
    
    # decrease Planned Qty of Prooduction Item by Qty
    get_obj('Warehouse', self.doc.fg_warehouse).update_bin(0, 0, 0, 0,-flt(self.doc.qty), self.doc.production_item, now())
