// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// define defaults for purchase common
cur_frm.cscript.tname = "Supplier Quotation Item";
cur_frm.cscript.fname = "quotation_items";
cur_frm.cscript.other_fname = "other_charges";

// attach required files
{% include 'buying/doctype/purchase_common/purchase_common.js' %};
{% include 'accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js' %}
{% include 'accounts/doctype/sales_invoice/pos.js' %}

erpnext.buying.SupplierQuotationController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		this._super();

		if (this.frm.doc.docstatus === 1) {
			cur_frm.add_custom_button(__("Make Purchase Order"), this.make_purchase_order,
				frappe.boot.doctype_icons["Journal Voucher"]);
		}
		else if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Material Request'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
						source_doctype: "Material Request",
						get_query_filters: {
							material_request_type: "Purchase",
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_ordered: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");
		}
	},

	make_purchase_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
			frm: cur_frm
		})
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.SupplierQuotationController({frm: cur_frm}));

cur_frm.cscript.uom = function(doc, cdt, cdn) {
	// no need to trigger updation of stock uom, as this field doesn't exist in supplier quotation
}

cur_frm.fields_dict['quotation_items'].grid.get_field('project_name').get_query =
	function(doc, cdt, cdn) {
		return{
			filters:[
				['Project', 'status', 'not in', 'Completed, Cancelled']
			]
		}
	}

cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return {
		filters:{'supplier': doc.supplier}
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return {
		filters:{'supplier': doc.supplier}
	}
}
