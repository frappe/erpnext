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
		// alert("jj")
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation",
			frm: cur_frm,
			run_link_triggers: true
		});
	}

});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.RequestforQuotationController({frm: cur_frm}));


cur_frm.fields_dict['supplier_detail'].grid.get_field('contact_person').get_query = function(doc, cdt, cdn){
	var d =locals[cdt][cdn];
	return {
		filters: {'supplier': d.supplier}
	}
}