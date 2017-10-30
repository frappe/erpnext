// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quotation Opening', {
    refresh: function(frm) {
        // cur_frm.trigger("get_sqs_filter");
        if (cur_frm.doc.docstatus === 1 && user_roles.indexOf("Purchase Manager") != -1) {
            cur_frm.add_custom_button(__("Purchase Order"), cur_frm.cscript['Make Purchase Order'],
                __("Make"));
            cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
        }

    },
    request_for_quotation: function(frm) {
        frappe.call({
            method: 'get_sqs_for_rfq',
            doc: cur_frm.doc,
            callback: function(r) {
                cur_frm.refresh_fields(["quotations"]);
            }
        });
        cur_frm.trigger("get_sqs_filter");

    },
    get_sqs_filter: function(frm) {
        frappe.call({
            method: 'get_sqs',
            doc: cur_frm.doc,
            args: {
                "flt": 1
            },
            callback: function(r) {
            	console.log(r.message);
                if (!r.message) {

                    cur_frm.toggle_enable("supplier_quotation", false)
                } else {

                    cur_frm.fields_dict['supplier_quotation'].get_query = function(doc, cdt, cdn) {
                        return {
                            filters: { 'name': ["in", r.message] }
                        }
                    }
                    cur_frm.toggle_enable("supplier_quotation", true)
                }
            }

        });
    }
});

cur_frm.cscript['Make Purchase Order'] = function() {
    frappe.model.open_mapped_doc({
        method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
        frm: cur_frm,
        source_name: cur_frm.doc.supplier_quotation
    })

}



// frappe.ui.form.on('Supplier Quotation Item', {
//             color_remove: function(frm) {
//                 // You code here
//                 // If you console.log(frm.doc.color) you will get the remaining color list
//             }
//         );