# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cint, flt
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
  def __init__(self, doc, doclist):
    self.doc = doc
    self.doclist = doclist

  def get_item_group(self):
    ret = sql("select name from `tabItem Group` ")
    item_group = []
    for r in ret:
      item =sql("select t1.name from `tabItem` t1, `tabBill Of Materials` t2 where t2.item = t1.name and t1.item_group = '%s' " % (r[0]))
      if item and item[0][0]:
        item_group.append(r[0])
    return '~~~'.join([r for r in item_group])

  def get_item_code(self,item_group):
    # here Bill Of Materials docstatus = 1 and is_active ='yes' condition is not given because some bom is under construction
    # that is it is still in saved mode and they want see till where they have reach.
    ret = sql("select distinct t1.name from `tabItem` t1, `tabBill Of Materials` t2 where t2.item = t1.name and t1.item_group = '%s' " % (item_group))
    return '~~~'.join([r[0] for r in ret])

  def get_bom_no(self,item_code):
    ret = sql("select name from `tabBill Of Materials` where item = '%s' " % (item_code))
    return '~~~'.join([r[0] for r in ret])

  def get_operations(self,bom_no):
    # reply = [ 'Operation',operation_no, opn_description,BOM NO     , workstation, hour_rate,  time_in_minutes,  Total Direct Material, Total Operating Cost, Cost]
    # reply = [ 0           ,  1         ,    2          ,3          , 4          ,  5        ,  6             ,         7            ,   8                 ,9                     , 10                  , 11  ]
    ret = sql("select operation_no,opn_description,workstation,hour_rate,time_in_mins from `tabBOM Operation` where parent = %s", bom_no, as_dict = 1)
    cost = sql("select dir_mat_as_per_mar , operating_cost , cost_as_per_mar from `tabBill Of Materials` where name = %s", bom_no, as_dict = 1)

    # Validate the BOM ENTRIES
    #check = get_obj('Bill Of Materials', bom_no, with_children =1).validate()
    reply = []

    if ret:
      for r in ret:
        reply.append(['operation',cint(r['operation_no']), r['opn_description'] or '','%s'% bom_no,r['workstation'],flt(r['hour_rate']),flt(r['time_in_mins']),0,0,0])

      reply[0][7]= flt(cost[0]['dir_mat_as_per_mar'])
      reply[0][8]=flt(cost[0]['operating_cost'])
      reply[0][9]=flt(cost[0]['cost_as_per_mar'])
    return reply

  def get_item_bom(self,data):
    # reply = ['item_bom',item_code,description,  BOM NO , qty, uom , scrap  ,m_avg_r  or value, 1 or 0]
    # reply = [ 0        ,  1      ,       2   ,   3     , 4  , 5   ,  6     ,   7             ,   8   ]
    data = eval(data)
    reply = []
    ret = sql("select item_code,description,bom_no,qty,scrap,stock_uom,value_as_per_mar,moving_avg_rate from `tabBOM Material` where parent = '%s' and operation_no = '%s'" % (data['bom_no'],data['op_no']), as_dict =1 )

    for r in ret:
      item = sql("select is_manufactured_item, is_sub_contracted_item from `tabItem` where name = '%s'" % r['item_code'], as_dict=1)
      if not item[0]['is_manufactured_item'] == 'Yes' and not item[0]['is_sub_contracted_item'] =='Yes':
        #msgprint("IS_PURCHASE")
        #if item is not manufactured or it is not sub-contracted
        reply.append([ 'item_bom', r['item_code'] or '', r['description'] or '', r['bom_no'] or '', flt(r['qty']) or 0, r['stock_uom'] or '', flt(r['scrap']) or 0, flt(r['moving_avg_rate']) or 0, 1])
      else:
        #msgprint("IS_NOT_PURCHASE")
        # if it is manufactured or sub_contracted this will be considered(here item can be purchase item)
        reply.append([ 'item_bom', r['item_code'] or '', r['description'] or '', r['bom_no'] or '', flt(r['qty']) or 0, r['stock_uom'] or '', flt(r['scrap']) or 0, flt(r['value_as_per_mar']) or 0, 0])
    return reply


  #------------- Wrapper Code --------------
  # BOM TREE
  def calculate_cost( self, bom_no):
    main_bom_list = get_obj(dt = 'Production Control').traverse_bom_tree( bom_no = bom_no, qty = 1, calculate_cost = 1)
    main_bom_list.reverse()
    for bom in main_bom_list:
      bom_obj = get_obj('Bill Of Materials', bom, with_children = 1)
      bom_obj.calculate_cost(validate = 0)
      bom_obj.doc.save()
    return 'calculated'


  def get_bom_tree_list(self,args):
    arg = eval(args)
    i =[]
    for a in sql("select t1.name from `tabBill Of Materials` t1, `tabItem` t2 where t2.item_group like '%s' and t1.item like '%s'"%(arg['item_group'] +'%',arg['item_code'] + '%')):
      if a[0] not in i:
        i.append(a[0])
    return i
#    return [s[0] for s in sql("select t1.name from `tabBill Of Materials` t1, `tabItem` t2 where t2.item_group like '%s'  and t1.item like '%s' " %(arg['item_group']+'%',arg['item_code'+'%'])]