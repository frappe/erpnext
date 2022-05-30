// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Packing Slip", {
	onload(frm) {
		frm.set_query("delivery_note", () => {
			return {
				filters: { 'docstatus': 0 }
			};
		});

		frm.set_query("item_code", "items", () => {
			if (!frm.doc.delivery_note) {
				frappe.throw(__("Please select a Delivery Note"));
			}

			return {
				query: "erpnext.stock.doctype.packing_slip.packing_slip.item_details",
				filters: { 'delivery_note': frm.doc.delivery_note }
			};
		});
	},

	onload_post_render(frm) {
		if (frm.doc.delivery_note && frm.doc.__islocal) {
			get_items(frm);
		}
	},

	refresh(frm) {
		frm.toggle_display("misc_details", frm.doc.amended_from);

		if (frm.doc.delivery_note && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Items"), () => get_items(frm));
		}
	},

	validate(frm) {
		validate_case_nos(frm.doc);
		validate_calculate_item_details(frm.doc);
	},

	scan_barcode(frm) {
		const barcode_scanner = new erpnext.utils.BarcodeScanner({
			frm,
			prompt_qty: frm.doc.prompt_qty
		});

		// snapshot of the document before being modified by barcode_scanner
		// in-case validation fails after the barcode is scanned we can use
		// this as a fallback to reference.
		const backup = frm.doc.items.map(item => ({...item}));

		function after_scan(scanned_row, exc_type) {
			if (exc_type === "InvalidPackingSlipItem") {
				frm.get_field("items").grid.grid_rows[scanned_row.idx - 1].remove();
				frappe.msgprint(__("Item {0} has automatically been removed from this packing slip.", [scanned_row.item_code]));
			} else if (exc_type === "InvalidPackedQty") {
				// Reset the qty to the value before the row was scanned.
				// If the row didn't exist, set the qty to zero.
				const row = backup.find(row => row.name === scanned_row.name);
				row.item_code = row.item_code ?? scanned_row.item_code;
				row.qty = row.qty ?? 0;

				frappe.model.set_value(row.doctype, row.name, "qty", row.qty, "Float");
				frappe.msgprint(__("Item {0} packed quantity has been reverted to {1}",
					[row.item_code, row.qty]));
			}
		}

		barcode_scanner.process_scan().then(scanned_row => {
			frm.call({
				doc: frm.doc,
				method: "validate_scanned_item"
			}).catch(({ responseJSON }) => {
				after_scan(scanned_row, responseJSON.exc_type);
			});
		});
	},

	delivery_note(frm) {
		frm.trigger("refresh");
	},

	from_case_no(frm) {
		const {doctype, name, from_case_no, to_case_no} = frm.doc;
		if (!to_case_no || to_case_no < from_case_no) {
			frappe.model.set_value(doctype, name, "to_case_no", from_case_no, "Int");
		}
	}
});

function get_items(frm) {
	return frm.call({
		doc: frm.doc,
		method: "get_items",
		callback: function(r) {
			if (!r.exc) frm.refresh();
		}
	});
}

// To Case No. cannot be less than From Case No.
function validate_case_nos(doc) {
	doc = locals[doc.doctype][doc.name];
	if (cint(doc.from_case_no)==0) {
		frappe.msgprint(__("The 'From Package No.' field must neither be empty nor it's value less than 1."));
		frappe.validated = false;
	} else if (!cint(doc.to_case_no)) {
		doc.to_case_no = doc.from_case_no;
		refresh_field('to_case_no');
	} else if (cint(doc.to_case_no) < cint(doc.from_case_no)) {
		frappe.msgprint(__("'To Case No.' cannot be less than 'From Case No.'"));
		frappe.validated = false;
	}
}


function validate_calculate_item_details(doc) {
	doc = locals[doc.doctype][doc.name];
	var ps_detail = doc.items || [];

	validate_duplicate_items(doc, ps_detail);
	calc_net_total_pkg(doc, ps_detail);
}


// Do not allow duplicate items i.e. items with same item_code
// Also check for 0 qty
function validate_duplicate_items(doc, ps_detail) {
	for (var i=0; i<ps_detail.length; i++) {
		for (var j=0; j<ps_detail.length; j++) {
			if (i!=j && ps_detail[i].item_code && ps_detail[i].item_code==ps_detail[j].item_code) {
				frappe.msgprint(__("You have entered duplicate items. Please rectify and try again."));
				frappe.validated = false;
				return;
			}
		}
		if (flt(ps_detail[i].qty)<=0) {
			frappe.msgprint(__("Invalid quantity specified for item {0}. Quantity should be greater than 0.", [ps_detail[i].item_code]));
			frappe.validated = false;
		}
	}
}


// Calculate Net Weight of Package
function calc_net_total_pkg (doc, ps_detail) {
	let net_weight_pkg = 0;
	doc.net_weight_uom = (ps_detail && ps_detail.length) ? ps_detail[0].weight_uom : '';
	doc.gross_weight_uom = doc.net_weight_uom;

	for (let i=0; i<ps_detail.length; i++) {
		const item = ps_detail[i];
		if (item.weight_uom != doc.net_weight_uom) {
			frappe.msgprint(__("Different UOM for items will lead to incorrect (Total) Net Weight value. Make sure that Net Weight of each item is in the same UOM."));
			frappe.validated = false;
		}
		net_weight_pkg += flt(item.net_weight) * flt(item.qty);
	}

	doc.net_weight_pkg = roundNumber(net_weight_pkg, 2);
	if (!flt(doc.gross_weight_pkg)) {
		doc.gross_weight_pkg = doc.net_weight_pkg;
	}
	refresh_many(['net_weight_pkg', 'net_weight_uom', 'gross_weight_uom', 'gross_weight_pkg']);
}

// TODO: validate gross weight field
