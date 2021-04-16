# # -*- coding: utf-8 -*-
# # Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# # For license information, please see license.txt

# from __future__ import unicode_literals
# # import frappe
# from frappe.model.document import Document

# class MaterialProduce(Document):
# 	pass

# -*- coding: utf-8 -*-
# Copyright (c) 2021, Dexciss Technology and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
import json
# from erpnext.manufacturing.doctype.bom.bom import add_additional_cost
from frappe.utils import cint, cstr, flt

class MaterialProduce(Document):
    @frappe.whitelist()
    def set_produce_material(self):
        if self.material_produce_details:
            total_qty = 0
            line_id = None
            for res in self.material_produce_details:
                total_qty += res.qty_produced
                line_id = res.line_ref

            l_doc = frappe.get_doc("Material Produce Item", line_id)
            # if l_doc.qty_produced:
            #     if total_qty > l_doc.qty_produced:
            #         pass
                    #frappe.throw(_("Can not allow total produced qty greater then {0}").format(l_doc.qty_produced))
            lst = []
            for res in self.material_produce_details:
                if res.qty_produced:
                    lst.append({
                        "item_code": res.item_code,
                        "item_name": res.item_name,
                        "t_warehouse": res.t_warehouse,
                        "qty_produced": res.qty_produced,
                        "has_batch_no": res.has_batch_no,
                        "batch": res.batch,
                        "rate": res.rate,
                        "weight": res.weight,
                        "line_ref": res.line_ref
                    })
            if line_id:
                l_doc = frappe.get_doc("Material Produce Item", line_id)
                l_doc.data = json.dumps(lst)
                l_doc.qty_produced = total_qty
                l_doc.status = "Set"
                l_doc.save(ignore_permissions=True)
        return True

    def on_submit(self):
        self.make_se()

    def make_stock_entry(self):
        return self.make_se()

    def make_se(self):
        wo = frappe.get_doc("Work Order",self.work_order)
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.work_order = self.work_order
        stock_entry.bom_no = wo.bom_no
        stock_entry.from_bom = 1
        stock_entry.use_multi_level_bom = wo.use_multi_level_bom
        stock_entry.material_produce = self.name
        stock_entry.company = self.company
        stock_entry.stock_entry_type = "Manufacture"
        total_transfer_qty = 0
        lst = []
        for res in self.material_produce_item:
            if res.status == 'Not Set':
                lst.append(0)
            else:
                lst.append(1)
        if 1 not in lst:
            frappe.throw(_("At least one Item required to be Produce"))

        wo = frappe.get_doc("Work Order",self.work_order)
        for res in self.material_produce_item:
            if res.type == "FG":
                total_transfer_qty += res.qty_produced
        for res in wo.required_items:
            qty = 0
            if res.transferred_qty:
                expense_account, cost_center = frappe.db.get_values("Company", self.company, ["default_expense_account", "cost_center"])[0]
                item_expense_account, item_cost_center = frappe.db.get_value("Item Default",
                                {'parent': res.item_code,'company': self.company},["expense_account","buying_cost_center"])
                if not cost_center and not item_cost_center:
                    frappe.throw(_("Please update default Cost Center for company {0}").format(self.company))
                if self.partial_produce:
                    if res.additional_material:
                        qty = res.transferred_qty
                    else:
                        bom = frappe.get_doc("BOM",wo.bom_no)
                        if bom.exploded_items:
                            query = frappe.db.sql("""select (bl.stock_qty / ifnull(b.quantity, 1)) as 'qty' 
                                from `tabBOM` as b 
                                inner join `tabBOM Explosion Item` as bl on bl.parent = b.name
                                where bl.item_code = %s and b.name = %s limit 1""",(res.item_code,bom.name))
                            if query:
                                qty = float(query[0][0]) * total_transfer_qty
                            else:
                                qty = res.transferred_qty
                        elif bom.scrap_items:
                            query = frappe.db.sql("""select (bl.stock_qty / ifnull(b.quantity, 1)) as 'qty' 
                                from `tabBOM` as b 
                                inner join `tabBOM Scrap Item` as bl on bl.parent = b.name
                                where bl.item_code = %s and b.name = %s limit 1""",(res.item_code,bom.name))
                            if query:
                                qty = float(query[0][0]) * total_transfer_qty
                            else:
                                qty = res.transferred_qty
                        else:
                            query = frappe.db.sql("""select (bl.qty / ifnull(b.quantity, 1)) as 'qty' 
                                from `tabBOM` as b 
                                inner join `tabBOM Item` as bl on bl.parent = b.name
                                where bl.item_code = %s and b.name = %s limit 1""",(res.item_code,bom.name))
                            if query:
                                qty = float(query[0][0]) * total_transfer_qty
                            else:
                                qty = res.transferred_qty
                else:
                    qty = res.transferred_qty - res.consumed_qty
                    stock_entry.completed_work_order = 1
                itm_doc = frappe.get_doc("Item",res.item_code)
                if qty > 0:
                    se_item = stock_entry.append("items")
                    se_item.item_code = res.item_code
                    se_item.qty = qty
                    se_item.s_warehouse = wo.wip_warehouse
                    se_item.item_name = itm_doc.item_name
                    se_item.description = itm_doc.description
                    se_item.uom = itm_doc.stock_uom
                    se_item.stock_uom = itm_doc.stock_uom
                    se_item.expense_account = item_expense_account or expense_account
                    se_item.cost_center = item_cost_center or cost_center
                    # in stock uom
                    se_item.conversion_factor = 1.00
        stock_entry.calculate_rate_and_amount(raise_error_if_no_rate=False)
        for res in self.material_produce_item:
            if res.data:
                for line in json.loads(res.data):
                    batch_no = None
                    if line.get('has_batch_no'):
                        batch_name = make_autoname(line.get('batch'))
                        batch_no = frappe.get_doc(dict(
                            doctype='Batch',
                            batch_id=batch_name,
                            item=line.get('item_code'),
                            supplier=getattr(self, 'supplier', None),
                            reference_doctype=self.doctype,
                            reference_name=self.name)).insert().name
                    expense_account, cost_center = frappe.db.get_values("Company", self.company, ["default_expense_account", "cost_center"])[0]
                    item_expense_account, item_cost_center = frappe.db.get_value("Item Default",
                                            {'parent': line.get('item_code'),'company': self.company},["expense_account","buying_cost_center"])
                    if not cost_center and not item_cost_center:
                        frappe.throw(_("Please update default Cost Center for company {0}").format(self.company))

                    itm_doc = frappe.get_doc("Item", line.get('item_code'))
                    if line.get('qty_produced') > 0:
                        se_item = stock_entry.append("items")
                        se_item.item_code = line.get('item_code')
                        se_item.qty = line.get('qty_produced')
                        se_item.t_warehouse = line.get('t_warehouse')
                        se_item.item_name = itm_doc.item_name
                        se_item.description = itm_doc.description
                        se_item.uom = res.uom
                        se_item.stock_uom = res.uom
                        se_item.batch_no = batch_no
                        se_item.expense_account = item_expense_account or expense_account
                        se_item.cost_center = item_cost_center or cost_center
                        se_item.is_finished_item = 1 if res.type == 'FG' else 0
                        se_item.is_scrap_item = 1 if res.type == 'Scrap' else 0
                        # in stock uom
                        se_item.conversion_factor = 1.00
            # if res.type == "FG":
            #     total_transfer_qty += res.qty_produced
        stock_entry.from_bom = 1
        stock_entry.fg_completed_qty = total_transfer_qty
        add_additional_cost(stock_entry, wo)
        stock_entry.set_actual_qty()
        stock_entry.set_missing_values()
        stock_entry.insert(ignore_permissions=True)
        stock_entry.validate()
        stock_entry.flags.ignore_validate_update_after_submit = True
        stock_entry.submit()
        return stock_entry.as_dict()


@frappe.whitelist()
def add_details_line(line_id, work_order, item_code, warehouse,qty_produced=None,batch_size=None, data=None, amount=None):
    if qty_produced:
        qty_produced = float(qty_produced)
    else:
        qty_produced = 0
    if batch_size:
        batch_size = float(batch_size)
    else:
        batch_size = 0
    if not data:
        item = frappe.get_doc("Item", item_code)
        lst = []
        batch_option = None
        enabled = frappe.db.get_single_value('Batch Settings', 'enabled')
        if enabled:
            is_finish_batch_series = frappe.db.get_single_value('Batch Settings', 'is_finish_batch_series')
            batch_series = frappe.db.get_single_value('Batch Settings', 'batch_series')
            if is_finish_batch_series == 'Use Work Order as Series':
                batch_option = str(work_order) + "-.##"
            if is_finish_batch_series == 'Create New':
                batch_option = batch_series
        else:
            if item.batch_number_series:
                batch_option = item.batch_number_series
            else:
                batch_option = str(work_order) + "-.##"
        if not amount:
            amount = 0
        else:
            amount = float(amount)
        if qty_produced > 1:
            per_item_rate = amount / qty_produced
        else:
            per_item_rate = 0

        if item.has_batch_no:
            remaining_size = qty_produced
            if batch_size:
                while True:
                    if (remaining_size >= batch_size):
                        lst.append({
                            "item_code": item.name,
                            "item_name": item.item_name,
                            "t_warehouse": warehouse,
                            "qty_produced": batch_size,
                            "has_batch_no": item.has_batch_no,
                            "batch": batch_option if item.has_batch_no else None,
                            "rate": per_item_rate,
                            "weight": item.weight_per_unit,
                            "line_ref": line_id
                        })
                    else:
                        lst.append({
                            "item_code": item.name,
                            "item_name": item.item_name,
                            "t_warehouse": warehouse,
                            "qty_produced": remaining_size,
                            "has_batch_no": item.has_batch_no,
                            "batch": batch_option if item.has_batch_no else None,
                            "rate": per_item_rate,
                            "weight": item.weight_per_unit,
                            "line_ref": line_id
                        })
                        break
                    remaining_size -= batch_size
                    if(remaining_size < 1):
                        break
            else:
                lst.append({
                    "item_code": item.name,
                    "item_name": item.item_name,
                    "t_warehouse": warehouse,
                    "qty_produced": qty_produced,
                    "has_batch_no": item.has_batch_no,
                    "batch": batch_option if item.has_batch_no else None,
                    "rate": per_item_rate,
                    "weight": item.weight_per_unit,
                    "line_ref": line_id
                })
        else:
            lst.append({
                "item_code": item.name,
                "item_name": item.item_name,
                "t_warehouse": warehouse,
                "qty_produced": qty_produced,
                "has_batch_no": item.has_batch_no,
                "weight": item.weight_per_unit,
                "rate": per_item_rate,
                "line_ref": line_id
            })
        return lst
    else:
        return json.loads(data)

def add_additional_cost(stock_entry, work_order):
    # Add non stock items cost in the additional cost
    stock_entry.additional_costs = []
    expenses_included_in_valuation = frappe.get_cached_value("Company", work_order.company,
        "expenses_included_in_valuation")

    add_non_stock_items_cost(stock_entry, work_order, expenses_included_in_valuation)
    add_operations_cost(stock_entry, work_order, expenses_included_in_valuation)


def add_non_stock_items_cost(stock_entry, work_order, expense_account):
    bom = frappe.get_doc('BOM', work_order.bom_no)
    table = 'exploded_items' if work_order.get('use_multi_level_bom') else 'items'

    items = {}
    for d in bom.get(table):
        items.setdefault(d.item_code, d.amount)

    non_stock_items = frappe.get_all('Item',
        fields="name", filters={'name': ('in', list(items.keys())), 'ifnull(is_stock_item, 0)': 0}, as_list=1)

    non_stock_items_cost = 0.0
    for name in non_stock_items:
        non_stock_items_cost += flt(items.get(name[0])) * flt(stock_entry.fg_completed_qty) / flt(bom.quantity)

    if non_stock_items_cost:
        stock_entry.append('additional_costs', {
            'expense_account': expense_account,
            'description': _("Non stock items"),
            'amount': non_stock_items_cost
        })

def add_operations_cost(stock_entry, work_order=None, expense_account=None):
    from erpnext.stock.doctype.stock_entry.stock_entry import get_operating_cost_per_unit
    operating_cost_per_unit = get_operating_cost_per_unit(work_order, stock_entry.bom_no)

    if stock_entry.material_produce:
        mp_doc = frappe.get_doc("Material Produce", stock_entry.material_produce)
        if not mp_doc.partial_produce:
            operating_cost_per_unit = (mp_doc.wo_actual_operation_cost - mp_doc.total_cost_of_operation_consumed) / stock_entry.fg_completed_qty
    if operating_cost_per_unit:
        stock_entry.append('additional_costs', {
            "expense_account": expense_account,
            "description": _("Operating Cost as per Work Order / BOM"),
            "amount": operating_cost_per_unit * flt(stock_entry.fg_completed_qty)
        })

    if work_order and work_order.additional_operating_cost and work_order.qty:
        additional_operating_cost_per_unit = \
            flt(work_order.additional_operating_cost) / flt(work_order.qty)

        if additional_operating_cost_per_unit:
            stock_entry.append('additional_costs', {
                "expense_account": expense_account,
                "description": "Additional Operating Cost",
                "amount": additional_operating_cost_per_unit * flt(stock_entry.fg_completed_qty)
            })
