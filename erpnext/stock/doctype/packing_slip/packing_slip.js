// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Packing Slip", {
    setup: (frm) => {
        frm.set_query('delivery_note', () => {
            return {
                filters: {
                    docstatus: 0,
                }
            }
        });

        frm.set_query('item_code', 'items', (doc, cdt, cdn) => {
            if (!doc.delivery_note) {
                frappe.throw(__("Please select a Delivery Note"));
            } else {
                let d = locals[cdt][cdn];
                return {
                    query: 'erpnext.stock.doctype.packing_slip.packing_slip.item_details',
                    filters: {
                        delivery_note: doc.delivery_note,
                    }
                }
            }
        });
	},

	refresh: (frm) => {
		frm.toggle_display("misc_details", frm.doc.amended_from);
	}
});
