# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import flt

class SubcontractProcessLoss(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.subcontracting.doctype.subcontract_process_loss_details.subcontract_process_loss_details import SubcontractProcessLossDetails
        from erpnext.subcontracting.doctype.subcontract_received_details.subcontract_received_details import SubcontractReceivedDetails
        from erpnext.subcontracting.doctype.subcontract_return_details.subcontract_return_details import SubcontractReturnDetails
        from erpnext.subcontracting.doctype.subcontract_sent_details.subcontract_sent_details import SubcontractSentDetails
        from frappe.types import DF
        from textiles_and_garments.textiles_and_garments.doctype.purchase_orders.purchase_orders import PurchaseOrders

        amended_from: DF.Link | None
        naming_series: DF.Literal["SPL/.####"]
        posting_date: DF.Date | None
        purchase_orders: DF.Table[PurchaseOrders]
        subcontract_process_loss_details: DF.Table[SubcontractProcessLossDetails]
        subcontract_received_details: DF.Table[SubcontractReceivedDetails]
        subcontract_return_details: DF.Table[SubcontractReturnDetails]
        subcontract_sent_details: DF.Table[SubcontractSentDetails]
    # end: auto-generated types
    pass


@frappe.whitelist()
def calculate_summary(docname):
    try:
        process_loss_doc = frappe.get_doc("Subcontract Process Loss", docname)

        sent_details = process_loss_doc.get("subcontract_sent_details", [])
        return_details = process_loss_doc.get("subcontract_return_details", [])
        received_details = process_loss_doc.get("subcontract_received_details", [])

        summary_data = {}

        # --------------------------
        # First, create a mapping from main_item_code to raw material details
        # --------------------------
        main_item_mapping = {}
        
        for sent_item in sent_details:
            main_item_code = sent_item.get("main_item_code") or sent_item.get("po_item_code")
            raw_item_code = sent_item.get("item_code")
            
            if main_item_code and main_item_code not in main_item_mapping:
                main_item_mapping[main_item_code] = {
                    "raw_item_code": raw_item_code,
                    "sent_uom": sent_item.get("uom"),
                    "po_qty": sent_item.get("po_qty", 0)
                }

        # --------------------------
        # Process Sent Details - Group by FINISHED PRODUCT (main_item_code)
        # --------------------------
        for sent_item in sent_details:
            main_item_code = sent_item.get("main_item_code") or sent_item.get("po_item_code")
            raw_item_code = sent_item.get("item_code")
            
            # Skip if main_item_code is None
            if not main_item_code:
                continue
            
            # Use FINISHED PRODUCT as the key
            key = (
                sent_item.get("purchase_order"),
                sent_item.get("subcontracting_order"),
                main_item_code  # Use the FINISHED PRODUCT code
            )

            if key not in summary_data:
                summary_data[key] = {
                    "purchase_order": sent_item.get("purchase_order"),
                    "subcontracting_order": sent_item.get("subcontracting_order"),
                    "item_code": main_item_code,  # Finished product
                    "raw_item_code": raw_item_code,  # Raw material
                    "uom": "",  # will be filled from received
                    "po_qty": 0,  # will be set from received_details later
                    "sent_qty": 0,
                    "return_qty": 0,
                    "received_qty": 0,
                    "sent_uom": sent_item.get("uom"),
                    "is_converted": False
                }

            summary_data[key]["sent_qty"] += flt(sent_item.get("sent_qty", 0))

        # --------------------------
        # Process Return Details - Group by FINISHED PRODUCT (po_item_code)
        # --------------------------
        for return_item in return_details:
            main_item_code = return_item.get("po_item_code")  # This is the finished product
            raw_item_code = return_item.get("item_code")  # This is the raw material
            
            # Skip if main_item_code is None
            if not main_item_code:
                continue
            
            # Use FINISHED PRODUCT as the key
            key = (
                return_item.get("purchase_order"),
                return_item.get("subcontracting_order"),
                main_item_code  # Use the FINISHED PRODUCT code
            )

            if key not in summary_data:
                # If no sent entry exists, create one with raw item mapping
                raw_mapping = main_item_mapping.get(main_item_code, {})
                summary_data[key] = {
                    "purchase_order": return_item.get("purchase_order"),
                    "subcontracting_order": return_item.get("subcontracting_order"),
                    "item_code": main_item_code,
                    "raw_item_code": raw_mapping.get("raw_item_code", raw_item_code),
                    "uom": "",
                    "po_qty": 0,
                    "sent_qty": 0,
                    "return_qty": 0,
                    "received_qty": 0,
                    "sent_uom": raw_mapping.get("sent_uom", ""),
                    "is_converted": False
                }

            summary_data[key]["return_qty"] += flt(return_item.get("return_qty", 0))

        # --------------------------
        # Process Received Details - Group by FINISHED PRODUCT (item_code)
        # --------------------------
        for received_item in received_details:
            main_item_code = received_item.get("item_code")  # This is the finished product
            
            # Skip if main_item_code is None
            if not main_item_code:
                continue
            
            # Use FINISHED PRODUCT as the key
            key = (
                received_item.get("purchase_order"),
                received_item.get("subcontracting_order"),
                main_item_code
            )

            if key not in summary_data:
                # If no sent/return entry exists, create one
                raw_mapping = main_item_mapping.get(main_item_code, {})
                summary_data[key] = {
                    "purchase_order": received_item.get("purchase_order"),
                    "subcontracting_order": received_item.get("subcontracting_order"),
                    "item_code": main_item_code,
                    "raw_item_code": raw_mapping.get("raw_item_code", ""),
                    "uom": received_item.get("uom"),
                    "po_qty": flt(received_item.get("po_qty", 0)),
                    "sent_qty": 0,
                    "return_qty": 0,
                    "received_qty": 0,
                    "sent_uom": raw_mapping.get("sent_uom", ""),
                    "is_converted": False
                }
            else:
                summary_data[key]["uom"] = received_item.get("uom")
                summary_data[key]["po_qty"] = flt(received_item.get("po_qty", 0))

            summary_data[key]["received_qty"] += flt(received_item.get("received_qty", 0))

        # --------------------------
        # Filter out entries with None item_code and distribute sent quantities
        # --------------------------
        filtered_summary_data = {}
        none_key_sent_qty = 0
        
        for key, data in summary_data.items():
            if data["item_code"] is None:
                # Store the sent quantity from the None item_code entry
                none_key_sent_qty += data["sent_qty"]
            else:
                filtered_summary_data[key] = data
        
        # Distribute the sent quantity from None entries to relevant finished products
        if none_key_sent_qty > 0 and filtered_summary_data:
            # Calculate distribution ratio based on po_qty
            total_po_qty = sum(data["po_qty"] for data in filtered_summary_data.values())
            if total_po_qty > 0:
                for key, data in filtered_summary_data.items():
                    distribution_ratio = data["po_qty"] / total_po_qty
                    distributed_sent_qty = none_key_sent_qty * distribution_ratio
                    data["sent_qty"] += distributed_sent_qty
        
        summary_data = filtered_summary_data

        
        # --------------------------
        # Calculate Process Loss
        # --------------------------
        subcontract_process_loss_details = []
        for key, data in summary_data.items():
            process_loss_qty = flt(data["sent_qty"]) - flt(data["return_qty"]) - flt(data["received_qty"])
            process_loss_percentage = 0
            if data["sent_qty"] > 0:
                process_loss_percentage = (process_loss_qty / data["sent_qty"]) * 100

            subcontract_process_loss_details.append({
                "purchase_order": data["purchase_order"],
                "subcontracting_order": data["subcontracting_order"],
                "item_code": data["item_code"],
                "uom": data["uom"],
                "po_qty": data["po_qty"],
                "sent_qty": data["sent_qty"],
                "return_qty": data["return_qty"],
                "received_qty": data["received_qty"],
                "process_loss_qty": process_loss_qty,
                "process_loss_percentage": process_loss_percentage
            })

        # --------------------------
        # Update Process Loss Doc (only items with valid item_code)
        # --------------------------
        process_loss_doc.set("subcontract_process_loss_details", [])

        for item in subcontract_process_loss_details:
            if item.get("item_code"):
                process_loss_doc.append("subcontract_process_loss_details", {
                    "purchase_order": item.get("purchase_order"),
                    "subcontracting_order": item.get("subcontracting_order"),
                    "item_code": item.get("item_code"),
                    "uom": item.get("uom"),
                    "po_qty": item.get("po_qty"),
                    "sent_qty": item.get("sent_qty"),
                    "return_qty": item.get("return_qty"),
                    "received_qty": item.get("received_qty"),
                    "process_loss_qty": item.get("process_loss_qty"),
                    "process_loss_percentage": item.get("process_loss_percentage")
                })

        process_loss_doc.save()
        frappe.db.commit()

        return subcontract_process_loss_details

    except Exception as e:
        frappe.log_error(f"Error calculating summary for {docname}: {str(e)}")
        frappe.throw(f"Failed to calculate summary: {str(e)}")
        return []


        


@frappe.whitelist()
def calculate_process_loss(docname, purchase_orders):
    if isinstance(purchase_orders, str):
        purchase_orders = json.loads(purchase_orders)
    
    # Extract only purchase_order values from non-empty rows
    purchase_order_list = [
        row.get("purchase_order") for row in purchase_orders
        if row.get("purchase_order") not in [None, ""]
    ]
    
    # Get the supplied items data
    all_supplied_items = get_subcontracting_order_details(purchase_order_list)
    
    # Update the Process Loss document with the sent_details
    update_sent_details(docname, all_supplied_items)
    
    # Get the returned items data for return_details table
    all_returned_items = get_returned_items_details(purchase_order_list)
    
    # Update the Process Loss document with the return_details
    update_return_details(docname, all_returned_items)
    
    # Get the received items data for received_details table
    all_received_items = get_received_items_details(purchase_order_list)
    
    # Update the Process Loss document with the received_details
    update_received_details(docname, all_received_items)
    
    return {
        'sent_details': all_supplied_items,
        'return_details': all_returned_items,
        'received_details': all_received_items
    }

def update_received_details(docname, received_details_data):
    """Update the received_details table in the Process Loss document"""
    try:
        # Get the Process Loss document
        process_loss_doc = frappe.get_doc("Subcontract Process Loss", docname)
        
        # Clear existing received_details
        process_loss_doc.set("subcontract_received_details", [])
        
        # Add new received_details rows
        for item in received_details_data:
            process_loss_doc.append("subcontract_received_details", {
                "purchase_order": item.get("purchase_order"),
                "subcontracting_order": item.get("subcontracting_order"),
                "item_code": item.get("item_code"),
                "po_qty": item.get("po_qty", 0),
                "po_rate": item.get("po_rate", 0),
                "received_qty": item.get("received_qty", 0),
                "subcontracting_receipt": item.get("subcontracting_receipt"),
                "purchase_receipt": item.get("purchase_receipt"),
                "bill_rate": item.get("pi_rate"),
                "bill_no": item.get("bill_no"),
                "diff_rate": item.get("diff_rate"),
                "purchase_invoice": item.get("purchase_invoice"),
                "uom": item.get("uom", "")
            })
        
        # Save the document
        process_loss_doc.save()
        frappe.db.commit()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error updating received_details for {docname}: {str(e)}")
        frappe.throw(f"Failed to update received details: {str(e)}")
        return False

def update_sent_details(docname, sent_details_data):
    """Update the sent_details table in the Process Loss document"""
    try:
        # Get the Process Loss document
        process_loss_doc = frappe.get_doc("Subcontract Process Loss", docname)
        
        # Clear existing sent_details
        process_loss_doc.set("subcontract_sent_details", [])
        
        # Add new sent_details rows
        for item in sent_details_data:
            process_loss_doc.append("subcontract_sent_details", {
                "purchase_order": item.get("purchase_order"),
                "subcontracting_order": item.get("subcontracting_order"),
                "item_code": item.get("item_code"),
                "po_item_code": item.get("main_item_code", ""),
                "po_qty": item.get("po_qty", 0),
                "sent_qty": item.get("sent_qty", 0),
                "stock_entry": item.get("stock_entry"),
                "uom": item.get("uom", "")
            })
        
        # Save the document
        process_loss_doc.save()
        frappe.db.commit()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error updating sent_details for {docname}: {str(e)}")
        frappe.throw(f"Failed to update sent details: {str(e)}")
        return False

def update_return_details(docname, return_details_data):
    """Update the return_details table in the Process Loss document"""
    try:
        # Get the Process Loss document
        process_loss_doc = frappe.get_doc("Subcontract Process Loss", docname)
        
        # Clear existing return_details
        process_loss_doc.set("subcontract_return_details", [])
        
        # Add new return_details rows
        for item in return_details_data:
            process_loss_doc.append("subcontract_return_details", {
                "purchase_order": item.get("purchase_order"),
                "subcontracting_order": item.get("subcontracting_order"),
                "item_code": item.get("item_code"),
                "po_item_code": item.get("po_item_code", ""),
                "po_qty": item.get("po_qty", 0),
                "return_qty": item.get("return_qty", 0),
                "stock_entry": item.get("stock_entry"),
                "uom": item.get("uom", "")
            })
        
        # Save the document
        process_loss_doc.save()
        frappe.db.commit()
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error updating return_details for {docname}: {str(e)}")
        frappe.throw(f"Failed to update return details: {str(e)}")
        return False

@frappe.whitelist()
def get_subcontracting_order_details(purchase_order_list):
    if not purchase_order_list:
        return []
    
    # Convert to tuple for SQL query
    po_tuple = tuple(purchase_order_list)
    
    # Get all Subcontracting Orders linked to these Purchase Orders
    sco_list = frappe.db.sql("""
        SELECT name, purchase_order, supplier_warehouse
        FROM `tabSubcontracting Order`
        WHERE purchase_order IN %s AND docstatus = 1
    """, (po_tuple,), as_dict=True)
    
    if not sco_list:
        return []
    
    # Get SCO names
    sco_names = [sco['name'] for sco in sco_list]
    sco_tuple = tuple(sco_names)
    
    # Get Subcontracting Order Supplied Items (raw materials)
    sco_supplied_items = frappe.db.sql("""
        SELECT 
            parent as subcontracting_order,
            rm_item_code as item_code,
            main_item_code,
            name,
            required_qty as po_qty
        FROM `tabSubcontracting Order Supplied Item`
        WHERE parent IN %s and docstatus = 1
    """, (sco_tuple,), as_dict=True)
    
    # Get UOM for each item from Item master
    item_codes = list(set([item['item_code'] for item in sco_supplied_items if item['item_code']]))
    item_uom_map = {}
    
    if item_codes:
        item_tuple = tuple(item_codes)
        item_data = frappe.db.sql("""
            SELECT item_code, stock_uom
            FROM `tabItem`
            WHERE item_code IN %s
        """, (item_tuple,), as_dict=True)
        
        item_uom_map = {item['item_code']: item['stock_uom'] for item in item_data}
    
    # Get all Stock Entries linked to these Subcontracting Orders for sent items
    stock_entries_data = get_stock_entries_for_sco(sco_names, 'Send to Subcontractor')
    
    # Combine data for sent_details
    sent_details = []
    
    for sco in sco_list:
        # Find supplied items for this SCO
        sco_items_filtered = [item for item in sco_supplied_items if item['subcontracting_order'] == sco['name']]
        
        # Find matching stock entries for this SCO
        matching_entries = [
            entry for entry in stock_entries_data 
            if entry['subcontracting_order'] == sco['name']
        ]
        
        for sco_item in sco_items_filtered:
            uom = item_uom_map.get(sco_item['item_code'], '')
            
            for entry in matching_entries:
                # Find matching items in the stock entry
                for stock_item in entry.get('items', []):
                    if stock_item.get('sco_rm_detail') == sco_item['name']:
                        sent_details.append({
                            'purchase_order': sco['purchase_order'],
                            'subcontracting_order': sco['name'],
                            'item_code': sco_item['item_code'],
                            'main_item_code': sco_item.get('main_item_code', ''),
                            'po_qty': sco_item['po_qty'],
                            'sent_qty': stock_item.get('qty', 0),
                            'stock_entry': entry['name'],
                            'uom': uom
                        })
    
    return sent_details

def get_returned_items_details(purchase_order_list):
    """Get returned items data for return_details table"""
    if not purchase_order_list:
        return []
    
    # Convert to tuple for SQL query
    po_tuple = tuple(purchase_order_list)
    
    # Get all Subcontracting Orders linked to these Purchase Orders with supplier_warehouse
    sco_list = frappe.db.sql("""
        SELECT name, purchase_order, supplier_warehouse
        FROM `tabSubcontracting Order`
        WHERE purchase_order IN %s AND docstatus = 1
    """, (po_tuple,), as_dict=True)
    
    if not sco_list:
        return []
    
    # Get SCO names
    sco_names = [sco['name'] for sco in sco_list]
    sco_tuple = tuple(sco_names)
    
    # Get supplier warehouses
    supplier_warehouses = [sco['supplier_warehouse'] for sco in sco_list if sco.get('supplier_warehouse')]
    
    if not supplier_warehouses:
        return []
    
    # Get all Stock Entries linked to these Subcontracting Orders with purpose "Material Transfer"
    # and where s_warehouse is the supplier_warehouse
    stock_entries_data = get_return_stock_entries_for_sco(sco_names, supplier_warehouses)
    
    # Get Subcontracting Order Supplied Items for main_item_code and po_qty mapping
    sco_supplied_items = frappe.db.sql("""
        SELECT 
            parent as subcontracting_order,
            rm_item_code as item_code,
            main_item_code,
            name,
            required_qty as po_qty
        FROM `tabSubcontracting Order Supplied Item`
        WHERE parent IN %s
    """, (sco_tuple,), as_dict=True)
    
    # Create mapping for main_item_code and po_qty
    item_main_item_map = {}
    item_po_qty_map = {}
    for item in sco_supplied_items:
        key = (item['subcontracting_order'], item['item_code'])
        item_main_item_map[key] = item.get('main_item_code', '')
        item_po_qty_map[key] = item.get('po_qty', 0)
    
    # Get UOM for each item from Item master
    item_codes = list(set([item['item_code'] for item in sco_supplied_items if item['item_code']]))
    item_uom_map = {}
    
    if item_codes:
        item_tuple = tuple(item_codes)
        item_data = frappe.db.sql("""
            SELECT item_code, stock_uom
            FROM `tabItem`
            WHERE item_code IN %s
        """, (item_tuple,), as_dict=True)
        
        item_uom_map = {item['item_code']: item['stock_uom'] for item in item_data}
    
    # Combine data for return_details
    return_details = []
    
    for sco in sco_list:
        # Find matching stock entries for this SCO
        matching_entries = [
            entry for entry in stock_entries_data 
            if entry['subcontracting_order'] == sco['name']
        ]
        
        for entry in matching_entries:
            for stock_item in entry.get('items', []):
                # Get main_item_code and po_qty from mapping
                key = (sco['name'], stock_item.get('item_code'))
                main_item_code = item_main_item_map.get(key, '')
                po_qty = item_po_qty_map.get(key, 0)
                
                uom = item_uom_map.get(stock_item.get('item_code'), '')
                
                return_details.append({
                    'purchase_order': sco['purchase_order'],
                    'subcontracting_order': sco['name'],
                    'item_code': stock_item.get('item_code'),
                    'po_item_code': main_item_code,
                    'po_qty': po_qty,  # Added po_qty here
                    'return_qty': stock_item.get('qty', 0),
                    'stock_entry': entry['name'],
                    'uom': uom
                })
    
    return return_details

def get_stock_entries_for_sco(sco_names, purpose):
    """Get stock entries for specific purpose"""
    if not sco_names:
        return []
    
    # Convert to tuple for SQL query
    sco_tuple = tuple(sco_names)
    
    stock_entry_list = frappe.db.sql("""
        SELECT name, subcontracting_order, purpose, posting_date
        FROM `tabStock Entry`
        WHERE subcontracting_order IN %s 
            AND docstatus = 1 
            AND (purpose LIKE 'Send to Subcontractor%%')
        ORDER BY posting_date
    """, (sco_tuple,), as_dict=True)
    
    # Fetch stock entry details for each stock entry
    for stock_entry in stock_entry_list:
        stock_entry['items'] = get_stock_entry_details(stock_entry['name'])
    
    return stock_entry_list

def get_return_stock_entries_for_sco(sco_names, supplier_warehouses):
    """Get return stock entries where s_warehouse is supplier_warehouse"""
    if not sco_names or not supplier_warehouses:
        return []
    
    # Convert to tuples for SQL query
    sco_tuple = tuple(sco_names)
    warehouse_tuple = tuple(supplier_warehouses)
    
    # Get all Stock Entries linked to these Subcontracting Orders with purpose "Material Transfer"
    # and where items have s_warehouse matching supplier_warehouse
    stock_entry_list = frappe.db.sql("""
        SELECT DISTINCT se.name, se.subcontracting_order, se.purpose, se.posting_date
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE se.subcontracting_order IN %s 
        AND se.docstatus = 1 
        AND se.purpose = 'Material Transfer'
        AND sed.s_warehouse IN %s
        ORDER BY se.posting_date
    """, (sco_tuple, warehouse_tuple), as_dict=True)
    
    # Fetch stock entry details for each stock entry
    for stock_entry in stock_entry_list:
        stock_entry['items'] = get_stock_entry_details(stock_entry['name'])
    
    return stock_entry_list

def get_stock_entry_details(stock_entry_name):
    """Fetch all items from Stock Entry Detail table for a given Stock Entry"""
    stock_entry_details = frappe.db.sql("""
        SELECT 
            item_code, qty, uom, sco_rm_detail,
            s_warehouse, t_warehouse, po_detail
        FROM `tabStock Entry Detail`
        WHERE parent = %s
        ORDER BY idx
    """, (stock_entry_name,), as_dict=True)
    
    return stock_entry_details

def get_received_items_details(purchase_order_list):
    """Get received items data from Subcontracting Receipt Item table"""
    if not purchase_order_list:
        return []
    
    # Convert to tuple for SQL query
    po_tuple = tuple(purchase_order_list)
    
    # Get all Subcontracting Orders linked to these Purchase Orders
    sco_list = frappe.db.sql("""
        SELECT name, purchase_order, supplier_warehouse
        FROM `tabSubcontracting Order`
        WHERE purchase_order IN %s AND docstatus = 1
    """, (po_tuple,), as_dict=True)
    
    if not sco_list:
        return []
    
    # Get SCO names
    sco_names = [sco['name'] for sco in sco_list]
    sco_tuple = tuple(sco_names)
    
    # Get all Subcontracting Receipt Items directly filtered by subcontracting_order
    receipt_items = frappe.db.sql("""
        SELECT 
            sri.parent as subcontracting_receipt,
            sri.name as subcontracting_receipt_item,
            sri.item_code,
            sri.qty as received_qty,
            sri.stock_uom,
            sri.subcontracting_order,
            sr.posting_date
        FROM `tabSubcontracting Receipt Item` sri
        INNER JOIN `tabSubcontracting Receipt` sr ON sri.parent = sr.name
        WHERE sri.subcontracting_order IN %s AND sr.docstatus = 1
        ORDER BY sr.posting_date
    """, (sco_tuple,), as_dict=True)
    
    if not receipt_items:
        return []
    
    # Get Subcontracting Order Items for po_qty and purchase_order_item mapping
    sco_order_items = frappe.db.sql("""
        SELECT 
            parent as subcontracting_order,
            item_code,
            qty as po_qty,
            purchase_order_item
        FROM `tabSubcontracting Order Item`
        WHERE parent IN %s
    """, (sco_tuple,), as_dict=True)
    
    # Create mapping for po_qty and purchase_order_item by (subcontracting_order, item_code)
    po_qty_map = {}
    purchase_order_item_map = {}
    for item in sco_order_items:
        key = (item['subcontracting_order'], item['item_code'])
        po_qty_map[key] = item.get('po_qty', 0)
        purchase_order_item_map[key] = item.get('purchase_order_item', '')
    
    # Get PO Rate from Purchase Order Item table
    purchase_order_items_list = list(set([item.get('purchase_order_item') for item in sco_order_items if item.get('purchase_order_item')]))
    po_rate_map = {}
    
    if purchase_order_items_list:
        po_item_tuple = tuple(purchase_order_items_list)
        purchase_order_items = frappe.db.sql("""
            SELECT 
                name,
                rate as po_rate
            FROM `tabPurchase Order Item`
            WHERE name IN %s
        """, (po_item_tuple,), as_dict=True)
        
        po_rate_map = {item['name']: item.get('po_rate', 0) for item in purchase_order_items}
    
    # Get UOM for each item from Item master (as fallback)
    item_codes = list(set([item['item_code'] for item in receipt_items if item['item_code']]))
    item_uom_map = {}
    
    if item_codes:
        item_tuple = tuple(item_codes)
        item_data = frappe.db.sql("""
            SELECT item_code, stock_uom
            FROM `tabItem`
            WHERE item_code IN %s
        """, (item_tuple,), as_dict=True)
        
        item_uom_map = {item['item_code']: item['stock_uom'] for item in item_data}
    
    # Create mapping from SCO name to purchase order
    sco_po_map = {sco['name']: sco['purchase_order'] for sco in sco_list}
    
    # Get all Purchase Receipts linked to these Subcontracting Receipts
    subcontracting_receipts = list(set([item['subcontracting_receipt'] for item in receipt_items]))
    pr_receipt_map = {}
    pr_items_map = {}
    
    if subcontracting_receipts:
        pr_tuple = tuple(subcontracting_receipts)
        # Get Purchase Receipts
        purchase_receipts = frappe.db.sql("""
            SELECT name, subcontracting_receipt
            FROM `tabPurchase Receipt`
            WHERE subcontracting_receipt IN %s AND docstatus = 1
        """, (pr_tuple,), as_dict=True)
        
        pr_receipt_map = {pr['subcontracting_receipt']: pr['name'] for pr in purchase_receipts}
        
        # Get Purchase Receipt Items with subcontracting_receipt_item reference
        purchase_receipt_names = list(pr_receipt_map.values())
        if purchase_receipt_names:
            pr_name_tuple = tuple(purchase_receipt_names)
            purchase_receipt_items = frappe.db.sql("""
                SELECT 
                    parent as purchase_receipt,
                    name as purchase_receipt_item,
                    subcontracting_receipt_item,
                    item_code,
                    qty,
                    rate,
                    amount
                FROM `tabPurchase Receipt Item`
                WHERE parent IN %s
            """, (pr_name_tuple,), as_dict=True)
            
            for pri in purchase_receipt_items:
                if pri['purchase_receipt'] not in pr_items_map:
                    pr_items_map[pri['purchase_receipt']] = {}
                pr_items_map[pri['purchase_receipt']][pri['subcontracting_receipt_item']] = pri
    
    # Get all Purchase Invoices linked to these Purchase Receipts
    purchase_receipt_names = list(pr_receipt_map.values())
    pi_receipt_map = {}  # Store list of PIs per PR
    pi_bill_map = {}
    pi_items_map = {}  # Store PI item details

    if purchase_receipt_names:
        pr_tuple = tuple(purchase_receipt_names)
        # Get Purchase Invoices linked to Purchase Receipts - Use DISTINCT to avoid duplicates
        purchase_invoices = frappe.db.sql("""
            SELECT DISTINCT pi.name, pi.bill_no, pii.purchase_receipt, pii.pr_detail
            FROM `tabPurchase Invoice` pi
            INNER JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            WHERE pii.purchase_receipt IN %s AND pi.docstatus != 2
        """, (pr_tuple,), as_dict=True)
        
        # Store unique PIs per PR using set to avoid duplicates
        for pi in purchase_invoices:
            if pi['purchase_receipt'] not in pi_receipt_map:
                pi_receipt_map[pi['purchase_receipt']] = set()  # Use set instead of list
            pi_receipt_map[pi['purchase_receipt']].add(pi['name'])  # Use add instead of append
            pi_bill_map[pi['name']] = pi.get('bill_no', '')
        
        # Convert sets back to lists for easier processing
        for pr in pi_receipt_map:
            pi_receipt_map[pr] = list(pi_receipt_map[pr])
        
        # Get Purchase Invoice Items for additional details
        purchase_invoice_names = list(set([pi['name'] for pi in purchase_invoices]))
        if purchase_invoice_names:
            pi_tuple = tuple(purchase_invoice_names)
            purchase_invoice_items = frappe.db.sql("""
                SELECT 
                    parent as purchase_invoice,
                    pr_detail,
                    item_code,
                    qty,
                    rate,
                    amount
                FROM `tabPurchase Invoice Item`
                WHERE parent IN %s
            """, (pi_tuple,), as_dict=True)
            
            for pii in purchase_invoice_items:
                if pii['purchase_invoice'] not in pi_items_map:
                    pi_items_map[pii['purchase_invoice']] = {}
                # Use pr_detail as the key (it contains the Purchase Receipt Item name)
                pi_items_map[pii['purchase_invoice']][pii['pr_detail']] = pii

    # Combine data for received_details - ONE ENTRY PER RECEIPT ITEM
    received_details = []
    
    for item in receipt_items:
        # Use UOM from receipt item, fallback to item master
        uom = item.get('stock_uom') or item_uom_map.get(item['item_code'], '')
        
        # Get purchase order from mapping
        purchase_order = sco_po_map.get(item['subcontracting_order'], '')
        
        # Get po_qty and purchase_order_item from mapping
        key = (item['subcontracting_order'], item['item_code'])
        po_qty = po_qty_map.get(key, 0)
        purchase_order_item = purchase_order_item_map.get(key, '')
        
        # Get po_rate from Purchase Order Item table
        po_rate = po_rate_map.get(purchase_order_item, 0)
        
        # Get linked Purchase Receipt
        purchase_receipt = pr_receipt_map.get(item['subcontracting_receipt'], '')
        
        # Get Purchase Receipt Item details using subcontracting_receipt_item
        pr_item_details = {}
        if purchase_receipt and purchase_receipt in pr_items_map:
            pr_item_details = pr_items_map[purchase_receipt].get(item['subcontracting_receipt_item'], {})
        
        # Get the Purchase Receipt Item name (this will be used as pr_detail)
        purchase_receipt_item_name = pr_item_details.get('purchase_receipt_item', '')
        
        # Get linked Purchase Invoices and Bill Nos (handle multiple PIs)
        purchase_invoices = pi_receipt_map.get(purchase_receipt, [])
        
        # Collect PI details for this PR item - Use dict to track unique PIs
        unique_pi_details = {}  # Use dict to store unique PI details by PI name

        for pi_name in purchase_invoices:
            # Get PI item details using purchase_receipt_item_name as pr_detail
            pi_item_details = {}
            if pi_name in pi_items_map and purchase_receipt_item_name:
                pi_item_details = pi_items_map[pi_name].get(purchase_receipt_item_name, {})
            
            if pi_item_details:  # Only add if there are actual details
                # Use PI name as key to ensure uniqueness
                unique_pi_details[pi_name] = {
                    'bill_no': pi_bill_map.get(pi_name, ''),
                    'qty': pi_item_details.get('qty', 0),
                    'rate': pi_item_details.get('rate', 0),
                    'amount': pi_item_details.get('amount', 0),
                    'diff_rate': pi_item_details.get('rate', 0) - po_rate
                }

        # Create lists from unique PI details
        pi_names = list(unique_pi_details.keys())
        bill_nos = [details['bill_no'] for details in unique_pi_details.values()]
        pi_qty_list = [details['qty'] for details in unique_pi_details.values()]
        pi_rate_list = [details['rate'] for details in unique_pi_details.values()]
        pi_amount_list = [details['amount'] for details in unique_pi_details.values()]
        diff_rate_list = [details['diff_rate'] for details in unique_pi_details.values()]
        
        # Create comma-separated values for multiple PIs
        purchase_invoice_list = ", ".join(pi_names) if pi_names else ''
        bill_no_list = ", ".join(bill_nos) if bill_nos else ''
        
        # Create comma-separated values for PI quantities, rates, amounts, and diff rates
        pi_qty_str = ", ".join([str(qty) for qty in pi_qty_list]) if pi_qty_list else '0'
        pi_rate_str = ", ".join([str(rate) for rate in pi_rate_list]) if pi_rate_list else '0'
        pi_amount_str = ", ".join([str(amount) for amount in pi_amount_list]) if pi_amount_list else '0'
        diff_rate_str = ", ".join([str(diff_rate) for diff_rate in diff_rate_list]) if diff_rate_list else '0'
        
        # Create only ONE entry per receipt item
        received_details.append({
            'purchase_order': purchase_order,
            'subcontracting_order': item['subcontracting_order'],
            'item_code': item['item_code'],
            'po_rate': po_rate,  # Use PO Rate from Purchase Order Item
            'po_qty': po_qty,
            'received_qty': item['received_qty'],
            'subcontracting_receipt': item['subcontracting_receipt'],
            'subcontracting_receipt_item': item['subcontracting_receipt_item'],
            'purchase_receipt': purchase_receipt,
            'purchase_receipt_item': purchase_receipt_item_name,
            'pr_detail': purchase_receipt_item_name,
            'pr_qty': pr_item_details.get('qty', 0),
            'pr_rate': pr_item_details.get('rate', 0),
            'pr_amount': pr_item_details.get('amount', 0),
            'purchase_invoice': purchase_invoice_list,  # Comma-separated list of unique PIs
            'bill_no': bill_no_list,  # Comma-separated list of unique Bill Nos
            'pi_qty': pi_qty_str,  # Comma-separated list of PI quantities
            'pi_rate': pi_rate_str,  # Comma-separated list of PI rates
            'pi_amount': pi_amount_str,  # Comma-separated list of PI amounts
            'diff_rate': diff_rate_str,  # Comma-separated list of rate differences
            'uom': uom
        })
    
    return received_details