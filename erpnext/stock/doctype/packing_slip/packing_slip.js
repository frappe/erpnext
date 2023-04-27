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

	onload_post_render: (frm) => {
		if(frm.doc.delivery_note && frm.doc.__islocal) {
			frm.trigger("get_items");
		}
	},

	get_items: (frm) => {
		return frm.call({
			doc: frm.doc,
			method: "get_items",
			callback: function(r) {
				if(!r.exc) {
					frm.refresh();
				}
			}
		});
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
		doc = locals[frm.doc.doctype][frm.doc.name];
		var ps_detail = doc.items || [];

		frm.events.validate_duplicate_items(doc, ps_detail);
		frm.events.calc_net_total_pkg(doc, ps_detail);
	},

	// Do not allow duplicate items i.e. items with same item_code
	// Also check for 0 qty
	validate_duplicate_items: (doc, ps_detail) => {
		for(var i=0; i<ps_detail.length; i++) {
			for(var j=0; j<ps_detail.length; j++) {
				if(i!=j && ps_detail[i].item_code && ps_detail[i].item_code == ps_detail[j].item_code) {
					frappe.msgprint(__("You have entered duplicate items. Please rectify and try again."));
					frappe.validated = false;
					return;
				}
			}

			if(flt(ps_detail[i].qty) <= 0) {
				frappe.msgprint(__("Invalid quantity specified for item {0}. Quantity should be greater than 0.", [ps_detail[i].item_code]));
				frappe.validated = false;
			}
		}
	},

	// Calculate Net Weight of Package
	calc_net_total_pkg: (doc, ps_detail) => {
		var net_weight_pkg = 0;
		doc.net_weight_uom = (ps_detail && ps_detail.length) ? ps_detail[0].weight_uom : '';
		doc.gross_weight_uom = doc.net_weight_uom;

		for(var i=0; i<ps_detail.length; i++) {
			var item = ps_detail[i];
			if(item.weight_uom != doc.net_weight_uom) {
				frappe.msgprint(__("Different UOM for items will lead to incorrect (Total) Net Weight value. Make sure that Net Weight of each item is in the same UOM."));
				frappe.validated = false;
			}
			net_weight_pkg += flt(item.net_weight) * flt(item.qty);
		}

		doc.net_weight_pkg = roundNumber(net_weight_pkg, 2);

		if(!flt(doc.gross_weight_pkg)) {
			doc.gross_weight_pkg = doc.net_weight_pkg;
		}

		refresh_many(['net_weight_pkg', 'net_weight_uom', 'gross_weight_uom', 'gross_weight_pkg']);
	}
});
