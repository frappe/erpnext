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
  # ---------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')


  def get_item_specification_details(self):
    self.doc.clear_table(self.doclist, 'qa_specification_details')
    specification = sql("select specification, value from `tabItem Specification Detail` where parent = '%s' order by idx" % (self.doc.item_code))
    for d in specification:
      child = addchild(self.doc, 'qa_specification_details', 'QA Specification Detail', 1, self.doclist)
      child.specification = d[0]
      child.value = d[1]
      child.status = 'Accepted'

  def on_submit(self):
    if self.doc.purchase_receipt_no:
      sql("update `tabPurchase Receipt Detail` set qa_no = '%s' where parent = '%s' and item_code = '%s'" % (self.doc.name, self.doc.purchase_receipt_no, self.doc.item_code))


  def on_cancel(self):
    if self.doc.purchase_receipt_no:
      sql("update `tabPurchase Receipt Detail` set qa_no = '' where parent = '%s' and item_code = '%s'" % (self.doc.purchase_receipt_no, self.doc.item_code))
