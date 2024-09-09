import frappe

@frappe.whitelist()
def cancel_and_draft_invoice(invoice_name):
    try:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
        invoice_doc.submit()
        invoice_doc.reload()
        
        #posa_is_printed = 0
        #invoice_payments = frappe.get_all("Sales Invoice Payment", filters={"parent": invoice_name}, fields=["name"])
        
        

        return True

    except Exception as e:
        frappe.log_error(f"Error in cancel_and_draft_invoice: {str(e)}")
        return False
