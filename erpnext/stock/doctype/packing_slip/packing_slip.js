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
	},

	validate: (frm) => {
		frm.trigger("validate_case_nos");
		frm.trigger("validate_calculate_item_details");
	},

	// To Case No. cannot be less than From Case No.
	validate_case_nos: (frm) => {
		doc = locals[frm.doc.doctype][frm.doc.name];

		if(cint(doc.from_case_no) == 0) {
			frappe.msgprint(__("The 'From Package No.' field must neither be empty nor it's value less than 1."));
			frappe.validated = false;
		} else if(!cint(doc.to_case_no)) {
			doc.to_case_no = doc.from_case_no;
			refresh_field('to_case_no');
		} else if(cint(doc.to_case_no) < cint(doc.from_case_no)) {
			frappe.msgprint(__("'To Case No.' cannot be less than 'From Case No.'"));
			frappe.validated = false;
		}
	},

	validate_calculate_item_details: (frm) => {
		frm.trigger("validate_items_qty");
		frm.trigger("calc_net_total_pkg");
	},

	validate_items_qty: (frm) => {
		frm.doc.items.forEach(item => {
			if (item.qty <= 0) {
				frappe.msgprint(__("Invalid quantity specified for item {0}. Quantity should be greater than 0.", [item.item_code]));
				frappe.validated = false;
			}
		});
	},

	calc_net_total_pkg: (frm) => {
		var net_weight_pkg = 0;
		var items = frm.doc.items || [];
		frm.doc.net_weight_uom = (items && items.length) ? items[0].weight_uom : '';
		frm.doc.gross_weight_uom = frm.doc.net_weight_uom;

		items.forEach(item => {
			if(item.weight_uom != frm.doc.net_weight_uom) {
				frappe.msgprint(__("Different UOM for items will lead to incorrect (Total) Net Weight value. Make sure that Net Weight of each item is in the same UOM."));
				frappe.validated = false;
			}
			net_weight_pkg += flt(item.net_weight) * flt(item.qty);
		});

		frm.doc.net_weight_pkg = roundNumber(net_weight_pkg, 2);

		if(!flt(frm.doc.gross_weight_pkg)) {
			frm.doc.gross_weight_pkg = frm.doc.net_weight_pkg;
		}

		refresh_many(['net_weight_pkg', 'net_weight_uom', 'gross_weight_uom', 'gross_weight_pkg']);
	}
});
