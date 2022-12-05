# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate

class AssetIssueDetails(Document):
    def validate(self):
        pass

    def on_submit(self):
        self.check_qty_balance()
        for i in range(cint(self.qty)):
            self.make_asset(i+1)

    def on_cancel(self):
        if self.reference_code:
            asset_status = frappe.db.get_value("Asset", self.reference_code, 'docstatus')
            if asset_status < 2:
                frappe.throw("You cannot cancel the document before cancelling asset with code {0}".format(self.reference_code))    
    
    def check_qty_balance(self):
        total_qty = frappe.db.sql("""select sum(ifnull(qty,0)) total_qty 
                                  from `tabAsset Received Entries`
                                  where item_code="{}"
                                  and ref_doc = "{}"
                                  and docstatus = 1
						""".format(self.item_code, self.purchase_receipt))[0][0]
        issued_qty = frappe.db.sql("""select sum(ifnull(qty,0)) issued_qty
                                   from `tabAsset Issue Details` 
                                   where item_code ='{}'
                                   and branch = '{}'
                                   and purchase_receipt = '{}'
                                   and docstatus = 1 
                                   and name != '{}'
						""".format(self.item_code, self.branch, self.purchase_receipt, self.name))[0][0]
        
        balance_qty = flt(total_qty) - flt(issued_qty)
        if flt(self.qty) > flt(balance_qty):
            frappe.throw(_("Issuing Quantity cannot be greater than Balance Quantity i.e., {}").format(flt(balance_qty)), title="Insufficient Balance")

    def make_asset(self, qty):       
        item_doc = frappe.get_doc("Item",self.item_code)
        if not cint(item_doc.is_fixed_asset):
            frappe.throw(_("Item selected is not a fixed asset"))

        if item_doc.asset_category:
            asset_category = frappe.db.get_value("Asset Category", item_doc.asset_category, "name")
            fixed_asset_account, credit_account=frappe.db.get_value("Asset Category Account", {'parent':asset_category}, ['fixed_asset_account','credit_account'])
            if item_doc.asset_sub_category:
                for a in frappe.db.sql("""select total_number_of_depreciations, income_depreciation_percent 
                                        from `tabAsset Finance Book` where parent = '{0}' 
                                        and `asset_sub_category`='{1}'
                                        """.format(asset_category, item_doc.asset_sub_category), as_dict=1):
                    total_number_of_depreciations = a.total_number_of_depreciations
                    depreciation_percent = a.income_depreciation_percent
            else:
                frappe.throw(_("No Asset Sub-Category for Item: " +"{}").format(self.item_name))
        else:
            frappe.throw(_("<b>Asset Category</b> is missing for material {}").format(frappe.get_desk_link("Item", self.item_code)))

        item_data = frappe.db.get_value(
            "Item", self.item_code, ["asset_naming_series", "asset_category","asset_sub_category"], as_dict=1
        )
        asset_abbr = frappe.db.get_value('Asset Category',item_data.get("asset_category"),'abbr')
        asset = frappe.get_doc(
			{
				"doctype": "Asset",
				"item_code": self.item_code,
				"asset_name": self.item_name,
				"naming_series": item_data.get("asset_naming_series") or "AST",
				"asset_category": item_data.get("asset_category"),
				"asset_sub_category":item_data.get("asset_sub_category"),
				"abbr": asset_abbr,
				"cost_center": frappe.db.get_value("Branch", self.branch, "cost_center"),
				"company": self.company,
				"purchase_date": self.issued_date,
				"calculate_depreciation": 1,
                "asset_rate": self.asset_rate,
				"purchase_receipt_amount": self.asset_rate,
				"gross_purchase_amount": flt(self.asset_rate) * flt(qty),
				"asset_quantity": qty,
				"purchase_receipt": self.purchase_receipt,
                "location": self.location,
                "branch": self.branch,
                "custodian": self.issued_to,
                "custodian_name": self.employee_name,
                "available_for_use_date": self.issued_date,
                "asset_account": fixed_asset_account,
                "credit_account": credit_account,
                "asset_issue_details":self.name,
                "serial_number":self.reg_number
			}
		)

        asset.flags.ignore_validate = True
        asset.flags.ignore_mandatory = True
        asset.set_missing_values()
        asset.insert()
        asset_code = asset.name
        
        if asset_code:
            self.db_set("reference_code", asset_code)
        else:
            frappe.throw("Asset not able to create for asset issue no.".format(self.name))

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)

    if user == "Administrator" or "System Manager" in user_roles: 
        return

    return """(
        exists(select 1
            from `tabEmployee` as e
            where e.branch = `tabAsset Issue Details`.branch
            and e.user_id = '{user}')
        or
        exists(select 1
            from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
            where e.user_id = '{user}'
            and ab.employee = e.name
            and bi.parent = ab.name
            and bi.branch = `tabAsset Issue Details`.branch)
    )""".format(user=user)

@frappe.whitelist()
def check_item_code(doctype, txt, searchfield, start, page_len, filters):
    cond = ""
    if not filters.get('item_code'):
        frappe.throw("Please select Item Code to fetch Purchase Receipt")
    if not filters.get("branch"):
        if not filters.get("cost_center"):
            frappe.throw("Please select Branch or Cost Center first.")
    if filters.get("branch"):
        cost_center = frappe.db.get_value("Branch",filters.get("branch"),"cost_center")
    if filters.get("cost_center"):
        cost_center = filters.get("cost_center")
    if filters.get('item_code'):
        cond += " ar.item_code = '{}'".format(filters.get('item_code'))
        cond += " and ar.cost_center = '{}'".format(cost_center)
    query = "select ar.ref_doc from `tabAsset Received Entries` ar where {cond}".format(cond=cond)
 
    return frappe.db.sql(query)

def update_branch():
    for a in frappe.db.sql("select *from `tabAsset Received Entries`", as_dict=True):
        branch = frappe.db.get_value("Branch", {'cost_center':a.cost_center}, 'branch')
        frappe.db.sql("update `tabAsset Received Entries` set branch = '{}' where name='{}'".format(branch,a.name))
    frappe.db.commit()
