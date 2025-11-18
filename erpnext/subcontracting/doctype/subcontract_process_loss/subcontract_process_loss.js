// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subcontract Process Loss", {
    refresh(frm) {

    },
    calculate_process_loss: function (frm) {
        frappe.call({
            method: 'erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_process_loss',
            args: {
                docname: frm.doc.name,
                purchase_orders: frm.doc.purchase_orders
            },
            callback: function (response) {
                if (response.message && Array.isArray(response.message)) {
                    console.log("Filtered stock items:", response.message);
                    // Reload the form to show the updated sent_details table
                    frm.reload_doc();
                    // frappe.show_alert({
                    //     message: __("Data updated successfully"),
                    //     indicator: 'green'
                    // }, 3000);
                }
            }
        });
    },
    calculate_summary: function (frm) {
        frappe.call({
            method: 'erpnext.subcontracting.doctype.subcontract_process_loss.subcontract_process_loss.calculate_summary',
            args: {
                docname: frm.doc.name,
            },
            callback: function (response) {
                if (response.message && Array.isArray(response.message)) {
                    console.log("Filtered stock items:", response.message);
                    // Reload the form to show the updated sent_details table
                    frm.reload_doc();
                    // frappe.show_alert({
                    //     message: __("Data updated successfully"),
                    //     indicator: 'green'
                    // }, 3000);
                }
            }
        });
    }
});
