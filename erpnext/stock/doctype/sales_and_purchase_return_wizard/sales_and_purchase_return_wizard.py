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

class DocType :
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

  # Pull Item Details
  # ---------------------------
  def pull_item_details(self):
    if self.doc.return_type == 'Sales Return':
      if self.doc.delivery_note_no:
        det = sql("select t1.name, t1.item_code, t1.description, t1.qty, t1.uom, t2.basic_rate, t3.customer, t3.customer_name, t3.customer_address, t2.serial_no, t2.batch_no from `tabDelivery Note Packing Detail` t1, `tabDelivery Note Detail` t2, `tabDelivery Note` t3 where t1.parent = t3.name and t2.parent = t3.name and t1.parent_detail_docname = t2.name and t3.name = '%s' and t3.docstatus = 1" % self.doc.delivery_note_no)
      elif self.doc.sales_invoice_no:
        det = sql("select t1.name, t1.item_code, t1.description, t1.qty, t1.stock_uom, t1.basic_rate, t2.customer, t2.customer_name, t2.customer_address, t1.serial_no from `tabRV Detail` t1, `tabReceivable Voucher` t2 where t1.parent = t2.name and t2.name = '%s' and t2.docstatus = 1" % self.doc.sales_invoice_no)
    elif self.doc.return_type == 'Purchase Return' and self.doc.purchase_receipt_no:
      det = sql("select t1.name, t1.item_code, t1.description, t1.received_qty, t1.uom, t1.purchase_rate, t2.supplier, t2.supplier_name, t2.supplier_address, t1.serial_no, t1.batch_no from `tabPurchase Receipt Detail` t1, `tabPurchase Receipt` t2 where t1.parent = t2.name and t2.name = '%s' and t2.docstatus = 1" % self.doc.purchase_receipt_no)

    self.doc.cust_supp = det and det[0][6] or ''
    self.doc.cust_supp_name = det and det[0][7] or ''
    self.doc.cust_supp_address = det and det[0][8] or ''
    self.create_item_table(det)
    self.doc.save()
 
  # Create Item Table
  # -----------------------------
  def create_item_table(self, det):
    self.doc.clear_table(self.doclist, 'return_details', 1)
    for i in det:
      ch = addchild(self.doc, 'return_details', 'Return Detail', 1, self.doclist)
      ch.detail_name = i and i[0] or ''
      ch.item_code = i and i[1] or ''
      ch.description = i and i[2] or ''
      ch.qty = i and flt(i[3]) or 0
      ch.uom = i and i[4] or ''
      ch.rate = i and flt(i[5]) or 0
      ch.serial_no = i and i[9] or ''
      ch.batch_no = (len(i) == 11) and i[10] or ''
      ch.save()

  # Clear return table
  # --------------------------------
  def clear_return_table(self):
    self.doc.clear_table(self.doclist, 'return_details', 1)
    self.doc.save()
