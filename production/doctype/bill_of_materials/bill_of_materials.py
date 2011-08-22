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

  def autoname(self):
    last_name = sql("select max(name) from `tabBill Of Materials` where name like 'BOM/%s/%%'" % self.doc.item)
    if last_name:
      idx = cint(cstr(last_name[0][0]).split('/')[-1]) + 1
    else:
      idx = 1
    self.doc.name = 'BOM/' + self.doc.item + ('/%.3i' % idx)

  #----------- Client Trigger function ----------
  def get_item_detail(self, item_code):
    item = sql("select description from `tabItem` where (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now()) and name = %s",item_code , as_dict =1)
    ret={
      'description'   : item and item[0]['description'] or ''
    }
    return ret

  def get_workstation_details(self,workstation):
    ws = sql("select hour_rate, capacity from `tabWorkstation` where name = %s",workstation , as_dict = 1)
    ret = {
      'hour_rate'            : ws and flt(ws[0]['hour_rate']) or '',
      'workstation_capacity' : ws and flt(ws[0]['capacity']) or ''
    }
    return ret

  def get_bom_material_detail(self, arg):
    arg = eval(arg)
    if arg['item_code'] and arg['item_code'] == self.doc.item:
      msgprint(" Item_code: "+arg['item_code']+" in materials tab cannot be same as main Item in BOM := " +cstr(self.doc.name))
      raise Exception
    if arg['item_code']:
      item = sql("select is_asset_item, is_purchase_item, docstatus, is_sub_contracted_item, description, stock_uom, default_bom from `tabItem` where item_code = %s", (arg['item_code']), as_dict = 1)

      # Check for Asset Item
      if item and item[0]['is_asset_item'] == 'Yes':
        msgprint("Sorry!!! Item " + arg['item_code'] + " is an Asset of the company. Entered in BOM := " + cstr(self.doc.name))
        raise Exception

      if item and item[0]['docstatus'] == 2:
        msgprint("Item %s does not exist in system" % cstr(args['item_code']))

      ret_item = {
                 'description' : item and item[0]['description'] or '',
                 'stock_uom'   : item and item[0]['stock_uom'] or '',
                 'bom_no'      : item and item[0]['default_bom'] or ''
      }

      # Check for Purchase Item
      if item and (item[0]['is_purchase_item'] == 'Yes' or item[0]['is_sub_contracted_item'] == 'Yes'):
        ret_item['moving_avg_rate'], ret_item['last_purchase_rate'], ret_item['standard_rate']  = self.get_mar_lpr_sr(arg['item_code'], mar = 1, lpr = 1, sr = 1)
        ret_item['operating_cost'], ret_item['dir_mat_as_per_mar'], ret_item['dir_mat_as_per_lpr'], ret_item['dir_mat_as_per_sr'] = 0, 0, 0, 0
        ret_item['value_as_per_mar'], ret_item['value_as_per_lpr'], ret_item['value_as_per_sr'] = 0, 0, 0
        ret_item['amount_as_per_mar'], ret_item['amount_as_per_lpr'], ret_item['amount_as_per_sr'] = 0, 0, 0

    if arg['bom_no'] or not ret_item['bom_no'] =='':
      if arg['bom_no']:
        bom = sql("select name, dir_mat_as_per_mar,dir_mat_as_per_lpr,dir_mat_as_per_sr, operating_cost, quantity from `tabBill Of Materials` where is_active = 'Yes' and name = %s", (arg['bom_no']), as_dict=1)
      else:
        # get recent direct material cost, operating_cost, cost from Default BOM of Item
        bom = sql("select name, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, operating_cost, quantity from `tabBill Of Materials` where is_active = 'Yes' and name = %s", (ret_item['bom_no']), as_dict=1)

      # get recent direct material cost, operating_cost, cost from Entered BOM of Item
      ret_item['bom_no'] = bom and bom[0]['name'] or ''

      if bom and bom[0]['name']:
        ret_bom = {
        'dir_mat_as_per_mar' : flt(bom[0]['dir_mat_as_per_mar']) / flt(bom[0]['quantity']) or 0.00,
        'dir_mat_as_per_lpr' : flt(bom[0]['dir_mat_as_per_lpr']) / flt(bom[0]['quantity']) or 0.00,
        'dir_mat_as_per_sr'  : flt(bom[0]['dir_mat_as_per_sr']) / flt(bom[0]['quantity']) or 0.00,
        'operating_cost'     : flt(bom[0]['operating_cost']) / flt(bom[0]['quantity']) or 0.00,
        'value_as_per_mar'   : ((flt(bom[0]['dir_mat_as_per_mar']) + flt(bom[0]['operating_cost'])) / flt(bom[0]['quantity'])) or 0.00,
        'value_as_per_lpr'   : ((flt(bom[0]['dir_mat_as_per_lpr']) + flt(bom[0]['operating_cost'])) / flt(bom[0]['quantity'])) or 0.00,
        'value_as_per_sr'    : ((flt(bom[0]['dir_mat_as_per_sr'])  + flt(bom[0]['operating_cost'])) / flt(bom[0]['quantity'])) or 0.00,
        'amount_as_per_mar'  : 0,
        'amount_as_per_lpr'  : 0,
        'amount_as_per_sr'   : 0
        }
        ret_item.update(ret_bom)
        if item and item[0]['is_sub_contracted_item'] != 'Yes':
          ret_bom_rates = {
            'moving_avg_rate'    : 0,
            'last_purchase_rate' : 0,
            'standard_rate'      : 0
            }
          ret_item.update(ret_bom_rates)
    return ret_item

  def set_as_default_bom(self):
    # set Is Default as 1
    set(self.doc,'is_default', flt(1))

    # get previous default bom from Item Master
    prev_def_bom = sql("select default_bom from `tabItem` where name = %s", self.doc.item,as_dict = 1)

    if prev_def_bom[0]['default_bom'] and prev_def_bom[0]['default_bom'] != self.doc.name:
      # update Is Default as 0 in Previous Default BOM
      msgprint(cstr(prev_def_bom[0]['default_bom']) + "is no longer Default BOM for item" + cstr(self.doc.item))
      sql("update `tabBill Of Materials` set is_default = 0 where name = '%s'" % (prev_def_bom[0]['default_bom']))

    # update current BOM as default bom in Item Master
    sql("update `tabItem` set default_bom = '%s' where name = '%s'" % (self.doc.name,self.doc.item))
    msgprint(cstr(self.doc.name) + "has been set as Default BOM for Item "+cstr(self.doc.item))

  def unset_as_default_bom(self):
    # set Is Default as 1
    set(self.doc,'is_default', flt(0))

    # update current BOM as default bom in Item Master
    sql("update `tabItem` set default_bom = null where name = '%s'" % (self.doc.item))
    msgprint(cstr(self.doc.name) + "has been unset as Default BOM for Item "+cstr(self.doc.item))

  def check_active_parent_boms(self):
    act_pbom = sql("select distinct t1.parent from `tabBOM Material` t1, `tabBill Of Materials` t2 where t1.bom_no ='%s' and t2.name = t1.parent and t2.is_active = 'Yes' and t2.docstatus = 1 and t1.docstatus =1 " % self.doc.name )
    if act_pbom and act_pbom[0][0]:
      msgprint("Sorry cannot Inactivate as BOM %s is child of one or many other active parent BOMs" % self.doc.name)
      raise Exception

  def activate_inactivate_bom(self, action):
    if cstr(action) == 'Activate':
      self.validate()
      set(self.doc, 'is_active', 'Yes')
    elif cstr(action) == 'Inactivate':
      self.check_active_parent_boms()
      set(self.doc, 'is_active', 'No')

  #------ On Validation Of Document ----------
  def validate_main_item(self):
    item = sql("select is_manufactured_item, is_sub_contracted_item from `tabItem` where name = %s and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now())", self.doc.item, as_dict = 1)

    if not item:
      msgprint("Item %s do not exists in the system. Entered in BOM := %s" % (cstr(self.doc.item), cstr(self.doc.name)))
      raise Exception

    elif not item[0]['is_manufactured_item'] == 'Yes' and not item[0]['is_sub_contracted_item'] == 'Yes':
      msgprint("Sorry cannot make Bill Of Materials for Item %s. As it is not a manufactured / sub-contracted item. Entered in BOM := %s " % (cstr(self.doc.item), cstr(self.doc.name)))
      raise Exception

  # validate operations
  #------------------------------------------------------
  def validate_operations(self,o,validate = "0"):
    if not o.operation_no:
      msgprint("Please Enter Operation No at Row " + cstr(o.idx)+" in BOM := " +cstr(self.doc.name))
      raise Exception

    if not o.workstation:
      msgprint("Please Enter Workstation for Operation No. " + cstr(o.operation_no) + " in BOM NO. " + self.doc.name)
      raise Exception

    if not o.time_in_mins:
      msgprint("Please Enter Operation Time of Operation No. " + cstr(o.operation_no)  + " in BOM NO. " + self.doc.name)
      raise Exception

    # Operation No should not repeat.
    if o.operation_no in self.op:
      msgprint("Operation No " + cstr(o.operation_no) + "is repeated in Operations Table of BOM NO. " + self.doc.name)
      raise Exception

      # add operation in op list
    self.op.append(cstr(o.operation_no))

  # Validate materials
  #-------------------------------------------------

  def validate_materials(self,m):

    # check for operation no
    if not self.op:
      msgprint("Please Enter Operations in operation table of BOM NO. " + self.doc.name)
      raise Exception

    # check if operation no not in op list
    if m.operation_no not in self.op:
      msgprint("Operation no "+ cstr(m.operation_no) + " for item code " + cstr(m.item_code) +" is not present in BOM Operations of BOM NO. " + self.doc.name)
      raise Exception

    if not m.item_code:
      msgprint("Please Enter Item Code at Row " + cstr(m.idx) + "of BOM Material in BOM NO. " + self.doc.name)
      raise Exception

    item = sql("select is_manufactured_item, is_sub_contracted_item from`tabItem` where item_code = %s and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life >  now())", m.item_code, as_dict = 1)
    if not item:
      msgprint("Item %s is not present in Item Master." % m.item_code)
      raise Exception

    if item[0]['is_manufactured_item'] == 'Yes' or item[0]['is_sub_contracted_item'] == 'Yes':
      bom = sql("select name, is_active, docstatus from `tabBill Of Materials` where item = %s", m.item_code, as_dict =1)
      if bom and bom[0]['name']:
        if not m.bom_no:
          msgprint("Please Enter BOM No for Item " + cstr(m.item_code) + " in Materials at Row No. " + cstr(m.idx)  + " in BOM NO. " + self.doc.name)
          raise Exception
        else:
          match = 0
          for b in bom:
            if cstr(m.bom_no) == cstr(b['name']):
              if b['is_active'] != 'Yes':
                msgprint("BOM %s NOT ACTIVE BOM. Entered in BOM := %s at row no := %s" % (cstr(m.bom_no), cstr(self.doc.name), m.idx))
                raise Exception

              #if flt(b['docstatus']) != 1:
              #  msgprint("BOM %s is NOT SUBMITTED."% cstr(m.bom_no))
              #  raise Exception

              match = 1
          if not match:
            msgprint("Item %s does not belongs to Bill Of Material %s or Bill Of Material %s is NOT ACTIVE BOM. Entered in BOM := %s at row no := %s" % (cstr(m.item_code),cstr(m.bom_no), cstr(m.bom_no), self.doc.name, m.idx))
            raise Exception

    if not item[0]['is_manufactured_item'] == 'Yes' and not item[0]['is_sub_contracted_item']== 'Yes':
      if m.bom_no:
        msgprint("As in Item Master of Item %s Is Manufactured Item / Is Sub-Contracted Item  is not 'Yes' hence there should be no BOM.In BOm := %s at row no := %s" % (m.item_code, cstr(self.doc.name), m.idx))
        raise Exception

    if not m.qty or m.qty <= 0:
      msgprint("Please Enter Qty value greater than 0(Zero) at Row " + cstr(m.idx) + " in BOM NO. " + self.doc.name)
      raise Exception

    if m.scrap and m.scrap < 0:
      msgprint("Please Enter Scrap value Greater than 0(Zero) at Row " + cstr(m.idx)  + " in BOM NO. " + self.doc.name)
      raise Exception

  # Calculate Cost
  #-----------------------------------------------

  def calculate_cost(self, validate = 0):
    self.op, op_cost, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, count_mat = [], 0.0, 0.0,0.0,0.0, 0
    # --------  Calculate Cost Of BOM  -------------
    # --- calculate operating cost from BOM Operations ----
    for o in getlist(self.doclist, 'bom_operations'):
      # --- Validation for enteries in BOM Operations ----
      if validate:
        self.validate_operations(o)

      o.operating_cost = flt(flt(o.time_in_mins)/60) * flt(o.hour_rate)
      if validate != 1:
        o.save()
        msgprint('Operation saved')

      op_cost = flt(op_cost) + flt(o.operating_cost)

    # --- calculate operating cost and direct material cost from BOM Material ---
    for m in getlist(self.doclist, 'bom_materials'):
      # --- Validation for enteries in BOM Material --- '''
      count_mat = count_mat + 1
      if validate:
        self.validate_materials(m)

      if m.bom_no:
        # add operating cost of child boms
        op_cost += flt(m.operating_cost)

        # update dir_mat, op_cost, value from child bom
        self.update_childs_dir_op_value(m, child_bom_cost = 1)

        # check for is_sub_contracted_item
        item = sql("select is_sub_contracted_item from `tabItem` where name = '%s'" % m.item_code, as_dict =1)
        if item and item[0]['is_sub_contracted_item'] == 'Yes':
          # update recent mar,lpr,sr
          self.update_mar_lpr_sr(m, mar =1, lpr =1, sr =1)
          # calculate amount for sub contracted item
          self.calculate_amount( m, has_bom = 1, is_sub_cont = 1)
          # calculate Direct Material
          dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr = self.calculate_dir_mat(m, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, has_bom = 1, is_sub_cont =1)
        else:
          # update mar,lpr,sr as 0
          self.update_mar_lpr_sr( m, mar = 0, lpr = 0, sr = 0)
          # calculate amount
          self.calculate_amount( m, has_bom = 1, is_sub_cont = 0)
          # calculate Direct Material
          dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr = self.calculate_dir_mat(m, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, has_bom = 1, is_sub_cont =0)

      else :
        # update dir_mat,op_cost, value as 0
        self.update_childs_dir_op_value(m, child_bom_cost = 0)
        # update recent mar,lpr,sr
        self.update_mar_lpr_sr(m, mar =1, lpr =1, sr =1)
        # calculate amount
        self.calculate_amount(m, has_bom = 0, is_sub_cont = 0)
        # calculate Direct Material
        dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr = self.calculate_dir_mat(m, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, has_bom =0, is_sub_cont =0)

      # update qty_consumed_per_unit
      m.qty_consumed_per_unit = flt(m.qty) / flt(self.doc.quantity)
      m.save()
      #msgprint("dir_mat_as_per_mar < ==> " + cstr(dir_mat_as_per_mar) + "***" + "dir_mat_as_per_lpr < ==> " + cstr(dir_mat_as_per_lpr) + "***" + "dir_mat_as_per_sr < ==> " + cstr(dir_mat_as_per_sr) + "***")
    if not count_mat:
      msgprint("There should at least one Item in BOM Material. In BOM := " +cstr(self.doc.name))
      raise Exception

    set(self.doc, 'operating_cost' ,op_cost)
    set(self.doc, 'cost_as_on' ,now())
    # update dir_mat
    set(self.doc, 'dir_mat_as_per_mar' ,dir_mat_as_per_mar)
    set(self.doc, 'dir_mat_as_per_lpr' ,dir_mat_as_per_lpr)
    set(self.doc, 'dir_mat_as_per_sr'  ,dir_mat_as_per_sr)
    # update cost
    set(self.doc, 'cost_as_per_mar' ,flt(dir_mat_as_per_mar + op_cost))
    set(self.doc, 'cost_as_per_lpr' ,flt(dir_mat_as_per_lpr + op_cost))
    set(self.doc, 'cost_as_per_sr' ,flt(dir_mat_as_per_sr + op_cost))

  def update_childs_dir_op_value(self, m, child_bom_cost = 0):
    #msgprint("IN UPDATE CHILDS DIR OP VALUE")
    if child_bom_cost:
      # get recent direct material cost, operating cost, cost from child bom
      child_bom_cost = sql("select dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, operating_cost, cost_as_per_mar, cost_as_per_lpr, cost_as_per_sr, quantity from `tabBill Of Materials` where  name = %s", m.bom_no, as_dict = 1)

    # operating_cost
    m.operating_cost = child_bom_cost and flt(child_bom_cost[0]['operating_cost']) / flt(child_bom_cost[0]['quantity']) or 0.00

    val_dir_dict = {'value_as_per_mar': 'cost_as_per_mar', 'dir_mat_as_per_mar': 'dir_mat_as_per_mar',
                    'value_as_per_lpr': 'cost_as_per_lpr', 'dir_mat_as_per_lpr': 'dir_mat_as_per_lpr',
                    'value_as_per_sr' : 'cost_as_per_sr' , 'dir_mat_as_per_sr' : 'dir_mat_as_per_sr'  }
    for d in val_dir_dict:
      # Set Value and Dir MAt
      m.fields[d] = child_bom_cost and flt(child_bom_cost[0][val_dir_dict[d]])/flt(child_bom_cost[0]['quantity']) or 0.00

  def update_mar_lpr_sr(self, m, mar = 0, lpr = 0, sr = 0):
    m.moving_avg_rate, m.last_purchase_rate, m.standard_rate = self.get_mar_lpr_sr(cstr(m.item_code), mar, lpr, sr, m.qty)

  def calculate_amount(self, m, has_bom = 0, is_sub_cont = 0):
    #msgprint("IN CALCULATE AMOUNT")
    if has_bom :
      m.amount_as_per_mar = flt(m.qty) * (is_sub_cont and flt(m.moving_avg_rate)  or flt(m.value_as_per_mar)) * flt(1.00 + (flt(m.scrap)/100)) or 0
      m.amount_as_per_lpr = flt(m.qty) * (is_sub_cont and (flt(m.value_as_per_lpr) + flt(m.last_purchase_rate)) or flt(m.value_as_per_lpr)) * flt(1.00 + (flt(m.scrap)/100)) or 0
      m.amount_as_per_sr  = flt(m.qty) * (is_sub_cont and (flt(m.value_as_per_sr)  + flt(m.standard_rate))      or flt(m.value_as_per_mar)) * flt(1.00 + (flt(m.scrap)/100)) or 0

    else:
      m.amount_as_per_mar = flt(m.qty) * flt(m.moving_avg_rate)    * flt(1.00 + (flt(m.scrap)/100)) or 0
      m.amount_as_per_lpr = flt(m.qty) * flt(m.last_purchase_rate) * flt(1.00 + (flt(m.scrap)/100)) or 0
      m.amount_as_per_sr = flt(m.qty)  * flt(m.standard_rate)      * flt(1.00 + (flt(m.scrap)/100)) or 0
    #msgprint(cstr(m.item_code))
    #msgprint("amount_as_per_mar < ==> " + cstr(m.amount_as_per_mar) + "***" + "amount_as_per_lpr < ==> " + cstr(m.amount_as_per_lpr) + "***" + "amount_as_per_sr < ==> " + cstr(m.amount_as_per_sr) + "***")
  def calculate_dir_mat(self, m, dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr, has_bom = 0, is_sub_cont =0):
    #msgprint("IN CALCULATE DIR MAT")
    if has_bom:
      dir_mat_as_per_mar +=  flt(m.qty) * (is_sub_cont and   flt(m.moving_avg_rate) or flt(m.dir_mat_as_per_mar)) * flt(1.00 + (flt(m.scrap)/100)) or 0
      dir_mat_as_per_lpr +=  flt(m.qty) * (is_sub_cont and ( flt(m.dir_mat_as_per_lpr)+ flt(m.last_purchase_rate)) or flt(m.dir_mat_as_per_lpr)) * flt(1.00 + (flt(m.scrap)/100)) or 0
      dir_mat_as_per_sr  +=  flt(m.qty) * (is_sub_cont and ( flt(m.dir_mat_as_per_sr)+ flt(m.standard_rate)     ) or flt(m.dir_mat_as_per_sr)) * flt(1.00 + (flt(m.scrap)/100)) or 0
    else:
      dir_mat_as_per_mar += flt(m.amount_as_per_mar)
      dir_mat_as_per_lpr += flt(m.amount_as_per_lpr)
      dir_mat_as_per_sr  += flt(m.amount_as_per_sr)
    #msgprint(cstr(m.item_code))
    #msgprint("dir_mat_as_per_mar < ==> " + cstr(dir_mat_as_per_mar) + "***" + "dir_mat_as_per_lpr < ==> " + cstr(dir_mat_as_per_lpr) + "***" + "dir_mat_as_per_sr < ==> " + cstr(dir_mat_as_per_sr) + "***")
    return dir_mat_as_per_mar, dir_mat_as_per_lpr, dir_mat_as_per_sr


  # Get FIFO Rate from Stack
  # -------------------------
  def get_fifo_rate(self, fcfs_bal, qty):
    if qty:
      fcfs_val = 0
      withdraw = flt(qty)
      while withdraw:
        if not fcfs_bal:
          break # nothing in store

        batch = fcfs_bal[0]

        if batch[0] < withdraw:
          # not enough in current batch, clear batch
          withdraw -= batch[0]
          fcfs_val += (flt(batch[0]) * flt(batch[1]))
          fcfs_bal.pop(0)
        else:
          # all from current batch
          fcfs_val += (flt(withdraw) * flt(batch[1]))
          batch[0] -= withdraw
          withdraw = 0
      fcfs_rate = flt(fcfs_val) / flt(qty)
      return fcfs_rate
    else:
      return fcfs_bal and fcfs_bal[0][1] or 0


  # Get valuation rate
  # --------------------
  def get_valuation_rate(self, item_code, qty):
    # get default warehouse
    warehouse = sql("select default_warehouse from tabItem where name = %s", item_code)
    warehouse = warehouse and warehouse[0][0] or ''
    in_rate = 0

    # get default valuation method
    val_method = sql("select valuation_method from tabItem where name = %s", item_code)
    val_method = val_method and val_method[0][0] or ''
    if not val_method: val_method = get_defaults().has_key('valuation_method') and get_defaults()['valuation_method'] or 'FIFO'

    if val_method == 'FIFO':
      if warehouse:
        bin_obj = get_obj('Warehouse',warehouse).get_bin(item_code)
        prev_sle = bin_obj.get_prev_sle('',nowdate(), (now().split(' ')[1])[:-3])
        fcfs_stack = prev_sle and (prev_sle[0][3] and eval(prev_sle[0][3]) or []) or []
      else:
        prev_sle = sql("select fcfs_stack from `tabStock Ledger Entry` where item_code = '%s' and posting_date <= '%s' order by posting_date DESC, posting_time DESC, name DESC limit 1" % (item_code, nowdate()))
        fcfs_stack = prev_sle and (prev_sle[0][0] and eval(prev_sle[0][0]) or []) or []
      in_rate = fcfs_stack and self.get_fifo_rate(fcfs_stack, qty) or 0
    elif val_method == 'Moving Average':
      in_rate = sql("select ifnull(sum(valuation_rate), 0)/ ifnull(count(*),1) from `tabBin` where item_code = '%s' and ifnull(ma_rate, 0) > 0" % cstr(item_code))
      in_rate = in_rate and flt(in_rate[0][0]) or 0
    return in_rate


  # Get valuation, Last Purchase and Standard Rate
  # ------------------------------------------------
  def get_mar_lpr_sr(self, item_code, mar = 0, lpr = 0, sr = 0, qty = 1.00):
    # get list of warehouse having
    ma_rate, lpr_rate, sr_rate = 0,0,0
    if mar:
      # get recent moving average rate
      #ma_rate = sql("select ifnull(sum(ma_rate), 0)/ ifnull(count(*),1) from `tabBin` where item_code = '%s' and ifnull(ma_rate, 0) > 0" % cstr(item_code))
      #ma_rate = flt(ma_rate and ma_rate[0][0]) or 0
      ma_rate = self.get_valuation_rate(item_code, qty)

    # get recent last purchase rate
    lpr_rate = lpr and flt(sql("select last_purchase_rate from `tabItem` where name = '%s'" % item_code)[0][0]) or 0.00
    # get recent standard rate
    sr_rate = sr and flt(sql("select standard_rate from `tabItem` where name = '%s'" % item_code)[0][0]) or 0.00
    return ma_rate, lpr_rate, sr_rate

  #checking for duplicate items i.e items that may be entered twice
  def validate_duplicate_items(self):
    check_list = []
    for d in getlist(self.doclist, 'bom_materials'):
      if cstr(d.item_code) in check_list:
        msgprint("Item %s has been entered twice. In BOM %s" % (d.item_code, self.doc.name))
        raise Exception
      else:
        check_list.append(cstr(d.item_code))

  #----- Document on Save function------
  def validate(self):
    #msgprint(len(getlist(self.doclist, 'bom_materials')))
    self.validate_main_item()
    self.validate_duplicate_items()
    self.calculate_cost(validate = 1)

  def check_recursion(self):
    check_list = [['parent', 'bom_no', 'parent'], ['bom_no', 'parent', 'child']]
    for d in check_list:
      bom_list, count = [self.doc.name], 0
      while ( len(bom_list) > count ):
        boms = sql(" select %s from `tabBOM Material` where %s = '%s' " % ( d[0], d[1], cstr(bom_list[count])))
        count = count + 1
        for b in boms:
          if b[0] == self.doc.name:
            msgprint("Recursion Occured:=>  '%s' cannot be '%s' of '%s'." % ( cstr(b), cstr(d[2]), cstr(self.doc.name)))
            raise Exception
          if b[0]:
            bom_list.append(b[0])

  def on_update(self):
    if self.doc.item != cstr(self.doc.name.split('/')[1]):
      msgprint("Cannot change Item once the Bill Of Material is created.")
      raise Exception
    self.check_recursion()


# ********************************************** Submit *************************************************************

  # Add Flat BOM Details
  # -----------------------
  def add_to_flat_bom_detail(self, is_submit = 0):
    self.doc.clear_table(self.doclist, 'flat_bom_details', 1)
    fb_lbl = {'item_code': 0, 'description': 1, 'qty': 2, 'stock_uom': 3, 'moving_avg_rate': 4,'amount_as_per_mar': 5, 'last_purchase_rate': 6, 'amount_as_per_lpr':7,'standard_rate':8,'amount_as_per_sr':9,'qty_consumed_per_unit': 10, 'parent_bom': 11, 'bom_mat_no': 12, 'is_pro_applicable': 13}
    for d in self.cur_flat_bom_items:
      fb_child = addchild(self.doc, 'flat_bom_details', 'Flat BOM Detail', 1, self.doclist)
      for i in fb_lbl:
        fb_child.fields[i] = d[fb_lbl[i]]
      fb_child.docstatus = is_submit
      fb_child.save(1)
    self.doc.save()


  #Get Child Flat BOM Items
  #----------------------------------------
  def get_child_flat_bom_items(self, item, d):

    child_flat_bom_items=[]
    if item and (item[0]['is_sub_contracted_item'] == 'Yes' or item[0]['is_pro_applicable'] == 'Yes'):

      child_flat_bom_items = sql("select item_code, description, qty_consumed_per_unit, stock_uom, moving_avg_rate, last_purchase_rate, standard_rate, '%s' as parent_bom, bom_mat_no, 'No' as is_pro_applicable from `tabFlat BOM Detail` where parent = '%s' and is_pro_applicable = 'No' and docstatus = 1" % ( d.bom_no, cstr(d.bom_no)))
      self.cur_flat_bom_items.append([d.item_code, d.description, flt(d.qty), d.stock_uom, flt(d.moving_avg_rate), flt(d.amount_as_per_mar), flt(d.last_purchase_rate), flt(d.amount_as_per_lpr), flt(d.standard_rate), flt(d.amount_as_per_sr), flt(d.qty_consumed_per_unit), (item[0]['is_sub_contracted_item'] == 'Yes') and d.parent or d.bom_no, d.name, (item[0]['is_sub_contracted_item'] == 'Yes') and 'No' or 'Yes'])

    else:
      child_flat_bom_items = sql("select item_code, description, qty_consumed_per_unit, stock_uom, moving_avg_rate, last_purchase_rate, standard_rate, if(parent_bom = '%s', '%s', parent_bom) as parent_bom, bom_mat_no, is_pro_applicable from `tabFlat BOM Detail` where parent = '%s' and docstatus = 1" % ( d.bom_no, d.parent, cstr(d.bom_no)))

    if not child_flat_bom_items:
      msgprint("Please Submit Child BOM := %s first." % cstr(d.bom_no))
      raise Exception
    else:
      return child_flat_bom_items


  # Get Current Flat BOM Items
  # -----------------------------
  def get_current_flat_bom_items(self):

    self.cur_flat_bom_items = []

    cfb_lbl = {'item_code': 0, 'description': 1, 'qty_consumed_per_unit': 2, 'stock_uom': 3, 'moving_avg_rate': 4, 'last_purchase_rate': 5, 'standard_rate': 6, 'parent_bom': 7, 'bom_mat_no': 8, 'is_pro_applicable': 9}

    for d in getlist(self.doclist, 'bom_materials'):

      if d.bom_no:
        item = sql("select is_sub_contracted_item, is_pro_applicable from `tabItem` where name = '%s'" % d.item_code, as_dict = 1)
        child_flat_bom_items = self.get_child_flat_bom_items(item,d)

        for c in child_flat_bom_items:
          self.cur_flat_bom_items.append([c[cfb_lbl['item_code']], c[cfb_lbl['description']], flt(d.qty) * flt(c[cfb_lbl['qty_consumed_per_unit']]), c[cfb_lbl['stock_uom']], flt(c[cfb_lbl['moving_avg_rate']]), flt(d.qty) * flt(c[cfb_lbl['qty_consumed_per_unit']]) * flt(c[cfb_lbl['moving_avg_rate']]) ,flt(c[cfb_lbl['last_purchase_rate']]), flt(d.qty) * flt(c[cfb_lbl['qty_consumed_per_unit']]) * flt(c[cfb_lbl['last_purchase_rate']]), flt(c[cfb_lbl['standard_rate']]), flt(d.qty) * flt(c[cfb_lbl['qty_consumed_per_unit']]) * flt(c[cfb_lbl['standard_rate']]), flt(d.qty_consumed_per_unit) * flt(c[cfb_lbl['qty_consumed_per_unit']]), c[cfb_lbl['parent_bom']], c[cfb_lbl['bom_mat_no']], c[cfb_lbl['is_pro_applicable']]])
      else:
        # add purchase_items from bom material to the child_flat_bom_items
        self.cur_flat_bom_items.append([d.item_code, d.description, flt(d.qty), d.stock_uom, flt(d.moving_avg_rate), flt(d.amount_as_per_mar), flt(d.last_purchase_rate), flt(d.amount_as_per_lpr), flt(d.standard_rate), flt(d.amount_as_per_sr), flt(d.qty_consumed_per_unit), d.parent, d.name, 'No' ])

  # Update Flat BOM Engine
  # ------------------------
  def update_flat_bom_engine(self, is_submit = 0):
    # following will be correct data
    # get correct / updated flat bom data
    self.get_current_flat_bom_items()
    # insert to curr flat bom data
    self.add_to_flat_bom_detail(is_submit)


  # On Submit
  # -----------
  def on_submit(self):
    self.update_flat_bom_engine(1)


  def get_parent_bom_list(self, bom_no):
    p_bom = sql("select parent from `tabBOM Material` where bom_no = '%s'" % bom_no)
    return p_bom and [i[0] for i in p_bom] or []
