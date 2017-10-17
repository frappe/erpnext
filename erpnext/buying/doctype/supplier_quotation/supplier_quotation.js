// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// attach required files
{% include 'erpnext/buying/doctype/purchase_common/purchase_common.js' %};

frappe.ui.form.on('Suppier Quotation', {
	setup: function() {
		frm.custom_make_buttons = {
			'Purchase Order': 'Purchase Order'
		}
	}
});

erpnext.buying.SupplierQuotationController = erpnext.buying.BuyingController.extend({
	refresh: function() {
		this._super();
		if (this.frm.doc.docstatus === 1) {
			cur_frm.add_custom_button(__("Purchase Order"), this.make_purchase_order,
				__("Make"));
			cur_frm.page.set_inner_btn_group_as_primary(__("Make"));
		}
		else if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('Material Request'),
				function() {
					erpnext.utils.map_current_doc({
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
				}, __("Get items from"));


			// var aa = [];
			// aa.push(cur_frm.doc.items);
			// var length = aa[0].length;

			// for(i=0;i<length;i++){
			// 	if(cur_frm.doc.items[i].material_request){
			// 		cur_frm.set_value('material_request', cur_frm.doc.items[i].material_request);
			// 		cur_frm.refresh_fields('material_request');
			// 	}
			// }



		}
	},

	make_purchase_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
			// frm: cur_frm
		})
	}


	// material_request: function(frm){


	// 	return frappe.call({
	// 	method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.get_project",
	// 	args: {
	// 	materialrequest: frm.doc.material_request,
	// 		},
	// 	callback: function(r) {
	// 		if (r.message) {
	// 		console.log(r.message)
	// 			}
	// 		}
	// 	});
	// }


});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.SupplierQuotationController({frm: cur_frm}));

cur_frm.fields_dict['items'].grid.get_field('project').get_query =
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
