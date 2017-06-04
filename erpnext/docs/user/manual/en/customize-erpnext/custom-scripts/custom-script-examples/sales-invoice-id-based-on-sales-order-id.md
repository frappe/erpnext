Below script allows you to get naming series in Sales Invoice, same as of corresponding Sales Order.
Invoice uses a prefix M- but the number duplicates the SO doc name (number).

Example: If Sales Order id is SO-12345, then corresponding Sales Invoice id will be set as M-12345.

    frappe.ui.form.on("Sales Invoice", "refresh", function(frm){
        var sales_order = frm.doc.items[0].sales_order.replace("M", "M-");
        if (!frm.doc.__islocal && sales_order && frm.doc.name!==sales_order){
            frappe.call({
            method: 'frappe.model.rename_doc.rename_doc',
            args: {
                doctype: frm.doctype,
                old: frm.docname,
                "new": sales_order,
                "merge": false
           },
        });
        }
    });
