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
    self.item_dict = {}
    self.defaults = get_defaults()
    
  def get_item_details(self, args):
    args = eval(args)
    item = sql("select description, stock_uom, default_bom from `tabItem` where name = '%s' and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now())" % args['item_code'], as_dict =1 )
    if item:
      ret = {'description' : item and item[0]['description'],
             'stock_uom'   : item and item[0]['stock_uom'],
             'bom_no'      : item and item[0]['default_bom']
      }
      return ret
    else:
      msgprint("Item %s does not exist in system." %(args['item_code']))
      raise Exception
    
  def validate_data(self):
    for d in getlist(self.doclist, 'pp_details'):
      if not d.pro_created:

        bom = sql("select name from `tabBill Of Materials` where item = %s and docstatus < 2", d.item_code, as_dict = 1)
        if d.bom_no and not bom:
          msgprint("There is no Active BOM for item code " + cstr(d.item_code) + " at row no." + cstr(d.idx)+ " which is Submitted. ")
          raise Exception
        if bom and bom[0]['name'] and not d.bom_no:
          msgprint("Please Enter BOM No. for item code " + cstr(d.item_code) + "at row no " + cstr(d.idx))
          raise Exception
        item = sql("select is_purchase_item from `tabItem` where name = %s", d.item_code,as_dict = 1)
#        if not item[0]['is_mrp_item']:
#          msgprint("Please Delete Row No " + cstr(d.idx) + " as Item " + cstr(d.item_code) + " is not MRP ITEM ")
#          raise Exception
        if not item[0]['is_purchase_item'] and not d.bom_no:
          msgprint("Please Delete Row No. "+ cstr(d.idx)+" as Item " + cstr(d.item_code) + " is not a PURCHASE ITEM ")
          raise Exception
        if not flt(d.planned_qty):
          msgprint("Please Enter Planned Qty for item code " + cstr(d.item_code) + "at row no " + cstr(d.idx))
          raise Exception
        if flt(d.prevdoc_reqd_qty) and flt(d.planned_qty) > flt(d.prevdoc_reqd_qty):
          msgprint(" Planned Qty cannot be greater than total Qty at row no " + cstr(d.idx))
          raise Exception
          
        item = sql("select is_manufactured_item, is_sub_contracted_item from`tabItem` where name = %s", d.item_code, as_dict = 1)
        if not item:
          msgprint("Item %s is not present in Item Master." % d.item_code)
          raise Exception

        if item[0]['is_manufactured_item'] == 'Yes' or item[0]['is_sub_contracted_item'] == 'Yes':
          bom = sql("select name, docstatus from `tabBill Of Materials` where item = %s", d.item_code, as_dict =1)
          if bom and bom[0]['name']:
            if not d.bom_no:
              msgprint("Please Enter BOM No for Item " + cstr(d.item_code) + " in Materials at Row No. " + cstr(d.idx)  + " in BOM NO. " + self.doc.name)
              raise Exception
            else:
              match = 0
              for b in bom:
                  if flt(b['docstatus']) > 1:
                    msgprint("BOM %s is NOT SUBMITTED."% cstr(d.bom_no))
                    raise Exception
              
                  match = 1
              if not match:
                msgprint("Item %s does not belong to Bill Of Material %s or Bill Of Material %s is NOT ACTIVE BOM." % (cstr(d.item_code),cstr(d.bom_no), cstr(d.bom_no)))
                raise Exception
    
        if not item[0]['is_manufactured_item'] == 'Yes' and not item[0]['is_sub_contracted_item']== 'Yes':
          if d.bom_no:
            msgprint("As in Item Master of Item %s Is Manufactured Item / Is Sub-Contracted Item  is not 'Yes' hence there should be no BOM." % d.item_code)
            raise Exception

    return 1

  def pull_document(self):
    if self.doc.sales_order:
      open_so = sql("select distinct 'Sales Order' as prevdoc, t1.name, ifnull(t1.transaction_date, ''), ifnull(t2.confirmation_date,'') from `tabSales Order` t1, `tabSales Order Detail` t2, `tabDelivery Note Packing Detail` t3 where ifnull(t3.planned_qty,0) < ifnull(t3.qty,0) and (t2.qty - ifnull(t2.delivered_qty,0)) > 0 and t3.parent_detail_docname =  t2.name and t2.parent = t1.name and t1.docstatus = 1 and t1.name = '%s' order by t1.transaction_date" % self.doc.sales_order)
      self.add_open_documents(open_so)
    #if self.doc.production_forecast:
      #open_pf = sql("select distinct 'Production Forecast' as prevdoc, t1.name, ifnull(t1.transaction_date,''), ifnull(t1.forecast_due_date,'') from `tabProduction Forecast` t1, `tabPF Detail` t2 where t2.planned_qty < t2.qty and t2.parent = t1.name and t1.name = '%s' and t1.docstatus = 1  order by t1.forecast_due_date " % self.doc.production_forecast)
      #self.add_open_documents(open_pf)
      
  def validate_duplicate_docname(self, check_data):
    for d in getlist(self.doclist, 'pp_so_details'):
      if [ d.prevdoc_docname, d.document_date, d.confirmation_date] == check_data :
        msgprint(cstr(d.prevdoc) + ": " + cstr(d.prevdoc_docname) + " appears more than once.")
        raise Exception
    
  def add_open_documents(self, open_doc):
    for r in open_doc:
      self.validate_duplicate_docname([r[1], r[2], r[3]])
      pp_so = addchild(self.doc, 'pp_so_details', 'PP SO Detail', 1, self.doclist)
      pp_so.prevdoc = r[0]
      pp_so.prevdoc_docname = r[1] 
      pp_so.document_date = cstr(r[2])
      pp_so.confirmation_date = cstr(r[3])
      pp_so.save()
 
  def get_open_docs(self):
    # Step 1:=> Remove unwanted rows from PP SO DETAIL TABLE
    self.remove_unwanted_rows_from_table(check_field ='include_in_plan', table_fname='pp_so_details')
    
    # Step 2:=> Check From Date should be before To Date
    if self.doc.from_date:
      if (getdate(self.doc.from_date) > getdate(self.doc.to_date)):
        msgprint("From Date cannot be after To Date")
        raise Exception
    
    # Step 3:=> At Least to date should be there
    if not self.doc.to_date:
      msgprint("To Date is Mandatory.")
      raise Exception

    # Step 4:=> GEt Open Sales ORder and Production Forecasts
    open_so = sql("select distinct 'Sales Order' as prevdoc, t1.name, t1.transaction_date, t2.confirmation_date from `tabSales Order` t1, `tabSales Order Detail` t2 where  (t2.qty - ifnull(t2.delivered_qty,0)) > 0 and t2.parent = t1.name %s and t1.transaction_date <= '%s' and t1.docstatus = 1 order by t1.transaction_date" % ((self.doc.from_date and "and t1.transaction_date >= '%s' " % self.doc.from_date or '') , self.doc.to_date))
    #open_pf = sql("select distinct 'Production Forecast' as prevdoc, t1.name, t1.transaction_date, t1.forecast_due_date from `tabProduction Forecast` t1, `tabPF Detail` t2 where ifnull(t2.planned_qty,0) < ifnull(t2.qty,0) and t1.name = t2.parent %s and t1.forecast_due_date <= '%s' and t1.docstatus = 1  order by t1.forecast_due_date " % ( self.doc.from_date and "and t1.forecast_due_date >= '%s' " % self.doc.from_date or '', self.doc.to_date))
    #open_doc = open_so + open_pf
    open_doc = open_so
    self.add_open_documents(open_doc)
    
  def remove_unwanted_rows_from_table(self, check_field, table_fname):
    for d in getlist(self.doclist, table_fname):
      if not d.fields[check_field]:
        d.fields['__oldparent'] = d.parent
        d.parent = 'old_parent:' + d.parent # for client to send it back while saving
        d.docstatus = 2
        if not d.fields.get('__islocal'):
          d.save()
      else:
        d.save()

  def get_packing_list_items(self, sales_order):
    #sales_com_obj.make_packing_list(self,'sales_order_details')
    pack_l = sql("select t2.name, t2.parent_item, t2.item_code, t0.transaction_date, t1.confirmation_date,(t1.qty - ifnull(t1.delivered_qty,0)) * (ifnull(t2.qty,0) / ifnull(t1.qty,1)) as 'pending_qty' from `tabSales Order` t0, `tabSales Order Detail` t1, `tabDelivery Note Packing Detail` t2 where ifnull(t2.planned_qty,0) < ifnull(t2.qty,0) and (t1.qty - ifnull(t1.delivered_qty,0)) > 0 and t2.parent_detail_docname = t1.name and t0.name = t1.parent and t1.parent = '%s' and t2.parent = '%s' and t1.docstatus =1 and t2.docstatus = 1" % (sales_order, sales_order), as_dict =1)
    for p in pack_l:
      pi = addchild(self.doc, 'pp_details', 'PP Detail', 0, self.doclist)
      pi.source_doctype        = 'Sales Order'
      pi.source_docname        = sales_order
      pi.source_detail_docname = p['name']
      pi.parent_item           = p['parent_item']
      pi.item_code             = p['item_code']
      pi.document_date         = cstr(p['transaction_date'])
      pi.confirmation_date     = cstr(p['confirmation_date'])
      item_details = sql("select description, stock_uom from tabItem where name=%s and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now())", p['item_code'])
      pi.description = item_details and item_details[0][0] or ''
      pi.stock_uom = item_details and item_details[0][1] or ''
      pi.prevdoc_reqd_qty = flt(p['pending_qty'])
      pi.save()
  
  def get_items(self):
    # Step 1:=> Remove unwanted rows from PP SO DETAIL TABLE
    self.remove_unwanted_rows_from_table(check_field ='include_in_plan', table_fname='pp_so_details')
    # Step 2:=> Remove unwanted rows from PP DETAIL TABLE
    self.doc.clear_table(self.doclist, 'pp_details', 1)
    # Step 3:=> Get All Details From Production Forecast and Sales Order which are marked Include In Plan in PP SO Detail
    for d in getlist(self.doclist, 'pp_so_details'):
      if d.include_in_plan:
        # Step 3.a :=> Get packing List items from sales order
        if d.prevdoc == 'Sales Order':
          self.get_packing_list_items(d.prevdoc_docname)
        # Step 3.b :=> Get Production Forecast items
        if d.prevdoc == 'Production Forecast':
          get_obj('DocType Mapper', 'Production Forecast-Production Planning Tool').dt_map('Production Forecast','Production Planning Tool', d.prevdoc_docname, self.doc, self.doclist, "[['Production Forecast','Production Planning Tool'],['PF Detail', 'PP Detail']]")

    self.set_defaults_pp_detail()

  def clear_table(self, table_name = ''):
    self.doc.clear_table(self.doclist, table_name, 1)

  def set_defaults_pp_detail(self):
    for d in getlist(self.doclist,'pp_details'):
      if not d.mrp:
        # set default BOM
        if not d.bom_no:
          bom = sql("select default_bom from `tabItem` where name = %s and (ifnull(end_of_life,'')='' or end_of_life ='0000-00-00' or end_of_life >  now())", d.item_code, as_dict = 1)
          if bom and bom[0]['default_bom']:
            d.bom_no = bom[0]['default_bom']
        # Set planned qty as prevdoc_reqd_qty 
        d.planned_qty = flt(d.prevdoc_reqd_qty)
        d.save()

  def make_items_dict(self, items_list):
    # items_list = [[item_name, qty]]
    for i in items_list:
      if self.item_dict.has_key(i[0]):
        self.item_dict[i[0]] = flt(self.item_dict[i[0]]) + flt(i[1])
      else:
        self.item_dict[i[0]] = flt(i[1])

  def get_raw_materials(self, bom_dict):
    for bom in bom_dict:
      # get all purchase items
      if self.doc.consider_sa_items == 'No':
        fl_bom_items = sql("select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s' from `tabFlat BOM Detail` where parent = '%s' and is_pro_applicable = 'No' and docstatus < 2 group by item_code" % (bom_dict[bom], bom))
        self.make_items_dict(fl_bom_items)
      
      # get all purchase items without sa child_items
      if self.doc.consider_sa_items == 'Yes':
        fl_bom_sa_items = sql("select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s' from `tabFlat BOM Detail` where parent = '%s' and parent_bom != '%s' and is_pro_applicable = 'Yes' and docstatus < 2 group by item_code" % (bom_dict[bom], bom, bom))
        self.make_items_dict(fl_bom_sa_items)
        fl_bom_items = sql("select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s' from `tabFlat BOM Detail` where parent = '%s' and parent_bom not in (select distinct parent_bom from `tabFlat BOM Detail` where parent = '%s' and parent_bom != '%s' and is_pro_applicable = 'Yes' and docstatus <2) and docstatus < 2 and is_pro_applicable = 'No' group by item_code" % (bom_dict[bom], bom, bom, bom) )
        self.make_items_dict(fl_bom_items)
        
    return self.item_dict
    
  def send_csv(self, item_dict):
    item_list = [['Item Code', 'Description', 'Stock UOM','Required Qty', 'Indented Qty', 'Ordered Qty', 'Actual Qty', ]]
    for d in item_dict:
      item_detail = sql("select description, stock_uom from `tabItem` where name = '%s'" % d)
      item_qty= sql("select sum(indented_qty), sum(ordered_qty), sum(actual_qty) from `tabBin` where item_code  = '%s' " % d)
      item_list.append([d, cstr(item_detail[0][0]), cstr(item_detail[0][1]), flt(item_dict[d]), item_qty and flt(item_qty[0][0]), item_qty and flt(item_qty[0][1]), item_qty and flt(item_qty[0][2])])
    return item_list
    
  def get_raw_materials_report(self):
    #self.validate_data()
    bom_dict = self.check_criteria_for_same_items(check_for = 'Report')
    item_dict = self.get_raw_materials(bom_dict)
    #msgprint(item_dict)
    #raise Exception
    return self.send_csv(item_dict)
    
  def raise_production_order(self):
    self.validate_data()
    pp_detail = self.check_criteria_for_same_items(check_for = 'Raise Production Order')
    pro = get_obj(dt = 'Production Control').create_production_order(self.doc.company, self.doc.fiscal_year, pp_detail = pp_detail)
    if len(pro) == 1:
      result = "Only Production Order " + cstr(pro[0]) + " has been generated."
    elif len(pro) > 1 :
      result = "Production Order From " + cstr(pro[0]) + " to "  + cstr(pro[len(pro) - 1]) +  " has been generated."
    else :
      result = " No Production Order is generated."
    msgprint(result)

  def check_criteria_for_same_items(self, check_for):
    pro_lbl = {'production_item': 0, 'description': 1, 'qty' : 2, 'stock_uom' : 3, 'bom_no': 4, 'consider_sa_items': 5}
    pp_detail, appended, bom_dict = [], 0, {}
    for d in getlist(self.doclist, 'pp_details'):
      if check_for == 'Report':
        if d.bom_no:
          if bom_dict.has_key(d.bom_no):
            bom_dict[d.bom_no] = flt(bom_dict[d.bom_no]) + flt(d.planned_qty)
          else:
            bom_dict[d.bom_no] = flt(d.planned_qty)
        else:
          self.make_items_dict([[d.item_code, d.planned_qty]])
          
      if check_for == 'Raise Production Order' and not d.pro_created:
        appended = 0
        if pp_detail:
          for i in pp_detail:
            # if same bom_no 
            if d.bom_no and d.bom_no == i[pro_lbl['bom_no']]:
              # set appended , add qty 
              appended, i[pro_lbl['qty']], d.pro_created = 1, i[pro_lbl['qty']] + flt(d.planned_qty) , 1
            
        if not appended and d.bom_no:
          pp_detail.append([d.item_code, d.description, d.planned_qty, d.stock_uom, d.bom_no, self.doc.consider_sa_items])
          d.pro_created = 1
        
        d.save()
    return (check_for =='Report') and bom_dict or pp_detail