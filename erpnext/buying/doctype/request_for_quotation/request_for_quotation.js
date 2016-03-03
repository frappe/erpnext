// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


{% include 'buying/doctype/purchase_common/purchase_common.js' %};

frappe.require("assets/erpnext/js/utils.js");

erpnext.buying.RequestforQuotationController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		this._super();

		if (this.frm.doc.docstatus === 1) {
			cur_frm.add_custom_button(__("Supplier Quotation"), this.make_suppplier_quotation,
				__("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
	},
	
	calculate_taxes_and_totals: function() {
		return;
	},
	
	tc_name: function() {
		this.get_terms();
	},
	
	make_suppplier_quotation: function() {
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
					"get_query": function () {
						return {
							query:"erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_supplier",
							filters: {'parent': cur_frm.doc.name}
						}
					}, "reqd": 1 },
				{"fieldtype": "Button", "label": __("Make Supplier Quotation"), "fieldname": "make_supplier_quotation", "cssClass": "btn-primary"},
			]
		});
		
		dialog.fields_dict.make_supplier_quotation.$input.click(function(){
			args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation",
				args: {
					"source_name": cur_frm.doc.name,
					"for_supplier": args.supplier
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						var doc = frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			});
		});
		dialog.show()
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.RequestforQuotationController({frm: cur_frm}));
