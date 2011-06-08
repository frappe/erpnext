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
    
  def search_parent_bom_of_bom(self):
    pbom = sql("select parent from `tabBOM Material` where bom_no = '%s' and docstatus = 1 " % self.doc.s_bom )
    self.doc.clear_table(self.doclist,'replace_bom_details', 1)
    self.add_to_replace_bom_utility_detail(pbom, 'replace_bom_details')
  
  def search_parent_bom_of_item(self):
    pbom = sql("select parent from `tabBOM Material` where item_code = '%s' and (bom_no is NULL or bom_no = '') and docstatus =1" % self.doc.s_item )
    self.doc.clear_table(self.doclist,'replace_item_details', 1)
    self.add_to_replace_bom_utility_detail(pbom, 'replace_item_details')
    
  def add_to_replace_bom_utility_detail(self, pbom, t_fname):
    for d in pbom:
      br_child = addchild( self.doc, t_fname, 'BOM Replace Utility Detail', 0,self.doclist)
      br_child.parent_bom = d[0]
      br_child.save()
    self.doc.save()  
    
  def replace_bom(self):
    # validate r_bom
    bom = sql("select name, is_active, docstatus from `tabBill Of Materials` where name = %s",self.doc.r_bom, as_dict =1)
    if not bom:
      msgprint("Please Enter Valid BOM to replace with.")
      raise Exception
    if bom and bom[0]['is_active'] != 'Yes':
      msgprint("BOM '%s' is not Active BOM." % cstr(self.doc.r_bom))
      raise Exception
    if bom and flt(bom[0]['docstatus']) != 1:
      msgprint("BOM '%s' is not Submitted BOM." % cstr(self.doc.r_bom))
      raise Exception
    
    # get item code of r_bom
    item_code = cstr(sql("select item from `tabBill Of Materials` where name = '%s' " % self.doc.r_bom)[0][0])
    # call replace bom engine
    self.replace_bom_engine('replace_bom_details', 'bom_no', self.doc.s_bom, self.doc.r_bom, item_code)
  
  def replace_item(self):
    item = sql("select name, is_active from `tabItem` where name = %s", self.doc.r_item, as_dict = 1)
    if not item:
      msgprint("Please enter Valid Item Code to replace with.")
      raise Exception
    if item and item[0]['is_active'] != 'Yes':
      msgprint("Item Code '%s' is not Active Item." % cstr(self.doc.r_item))
      raise Exception
    self.replace_bom_engine('replace_item_details', 'item_code', self.doc.s_item, self.doc.r_item)
    
  def replace_data_in_bom_materials(self, dl, fname, s_data, r_data, item_code =''):
    for d in getlist(dl, 'bom_materials'):
      if d.fields[fname] == s_data:
        d.fields[fname] = r_data
        if fname == 'bom_no':
          d.item_code = item_code
        d.save()

  def replace_bom_engine(self, t_fname, fname, s_data, r_data, item_code = ''):
    if not r_data:
      msgprint("Please Enter '%s' and then click on '%s'." % ((t_fname == 'replace_bom_details') and 'BOM to Replace' or 'Item to Replace',(t_fname == 'replace_bom_details') and 'Replace BOM' or 'Replace Item' ))
      raise Exception
      
    for d in getlist(self.doclist, t_fname):
      if d.bom_created:
        msgprint("Please click on '%s' and then on '%s'." % ((t_fname == 'replace_bom_details') and 'Search BOM' or 'Search Item',(t_fname == 'replace_bom_details') and 'Replace BOM' or 'Replace Item' ))
        raise Exception
        
      if d.replace:
        # copy_doclist is the framework funcn which create duplicate document and returns doclist of new document
        # Reinder := 
        # make copy
        if self.doc.create_new_bom:
          import webnotes.model.doc
          new_bom_dl = copy_doclist(webnotes.model.doc.get('Bill Of Materials', d.parent_bom), no_copy = ['is_active', 'is_default', 'is_sub_assembly', 'remarks', 'flat_bom_details'])
        
          new_bom_dl[0].docstatus = 0
          new_bom_dl[0].save()
        else:
          new_bom_dl = get_obj('Bill Of Materials', d.parent_bom, with_children = 1).doclist

        # replace s_data with r_data in Bom Material Detail Table
        self.replace_data_in_bom_materials(new_bom_dl, fname, s_data, r_data, item_code)
       
        d.bom_created = new_bom_dl[0].name
        d.save()

  def update_docstatus(self):
    sql("update `tabBill Of Materials` set docstatus = 0 where  name = '%s' limit 1" % self.doc.bom)
    msgprint("Updated")

  def update_bom(self):
    self.check_bom_list = []
    main_bom_list = get_obj('Production Control').traverse_bom_tree(self.doc.fg_bom_no, 1)
    main_bom_list.reverse()
    # run calculate cost and get
    #msgprint(main_bom_list)
    for bom in main_bom_list:
      if bom and bom not in self.check_bom_list:
        bom_obj = get_obj('Bill Of Materials', bom, with_children = 1)
        #print(bom_obj.doc.fields)
        bom_obj.validate()
        bom_obj.doc.docstatus = 1
        bom_obj.check_recursion()
        bom_obj.update_flat_bom_engine(is_submit = 1)
        bom_obj.doc.docstatus = 1
        bom_obj.doc.save()
        self.check_bom_list.append(bom)
