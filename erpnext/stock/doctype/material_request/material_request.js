// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Material Request Item";
cur_frm.cscript.fname = "indent_details";

{% include 'buying/doctype/purchase_common/purchase_common.js' %};

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	onload: function(doc) {
		this._super();
		this.frm.set_query("item_code", this.frm.cscript.fname, function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			}
		});
	},

	refresh: function(doc) {
		this._super();

		// dashboard
		cur_frm.dashboard.reset();
		if(doc.docstatus===1) {
			if(doc.status==="Stopped") {
				cur_frm.dashboard.set_headline_alert(__("Stopped"), "alert-danger", "icon-stop")
			}
			cur_frm.dashboard.add_progress(cint(doc.per_ordered) + "% "
				+ __("Fulfilled"), cint(doc.per_ordered));
		}

		if(doc.docstatus==0) {
			cur_frm.add_custom_button(__("Get Items from BOM"),
				cur_frm.cscript.get_items_from_bom, "icon-sitemap", "btn-default");
		}

		if(doc.docstatus == 1 && doc.status != 'Stopped') {
			if(doc.material_request_type === "Purchase")
				cur_frm.add_custom_button(__("Make Supplier Quotation"),
					this.make_supplier_quotation,
						frappe.boot.doctype_icons["Supplier Quotation"]);

			if(doc.material_request_type === "Transfer" && doc.status === "Submitted")
				cur_frm.add_custom_button(__("Transfer Material"), this.make_stock_entry,
					frappe.boot.doctype_icons["Stock Entry"]);

			if(flt(doc.per_ordered, 2) < 100) {
				if(doc.material_request_type === "Purchase")
					cur_frm.add_custom_button(__('Make Purchase Order'),
						this.make_purchase_order, frappe.boot.doctype_icons["Purchase Order"]);

				cur_frm.add_custom_button(__('Stop'),
					cur_frm.cscript['Stop Material Request'], "icon-exclamation", "btn-default");
			}
			cur_frm.add_custom_button(__('Send SMS'), cur_frm.cscript.send_sms,
				"icon-mobile-phone", true);

		}

		if (this.frm.doc.docstatus===0) {
			cur_frm.add_custom_button(__('From Sales Order'),
				function() {
					frappe.model.map_current_doc({
						method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
						source_doctype: "Sales Order",
						get_query_filters: {
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_delivered: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				}, "icon-download", "btn-default");
		}

		if(doc.docstatus == 1 && doc.status == 'Stopped')
			cur_frm.add_custom_button(__('Unstop Material Request'),
				cur_frm.cscript['Unstop Material Request'], "icon-check");

	},

	schedule_date: function(doc, cdt, cdn) {
		var val = locals[cdt][cdn].schedule_date;
		if(val) {
			$.each((doc.indent_details || []), function(i, d) {
				if(!d.schedule_date) {
					d.schedule_date = val;
				}
			});
			refresh_field("indent_details");
		}
	},

	get_items_from_bom: function() {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1},
				{fieldname:"fetch", "label":__("Get Items from BOM"), "fieldtype":"Button"}
			]
		});
		d.get_input("fetch").on("click", function() {
			var values = d.get_values();
			if(!values) return;

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
				args: values,
				callback: function(r) {
					$.each(r.message, function(i, item) {
						var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "indent_details");
						d.item_code = item.item_code;
						d.description = item.description;
						d.warehouse = item.default_warehouse;
						d.uom = item.stock_uom;
						d.qty = item.qty;
					});
					d.hide();
					refresh_field("indent_details");
				}
			});
		});
		d.show();
	},

	tc_name: function() {
		this.get_terms();
	},

	validate_company_and_party: function(party_field) {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	make_purchase_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
			frm: cur_frm
		})
	},

	make_supplier_quotation: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
			frm: cur_frm
		})
	},

	make_stock_entry: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_stock_entry",
			frm: cur_frm
		})
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (flt(d.qty) < flt(d.min_order_qty))
		alert(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
};

cur_frm.cscript['Stop Material Request'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(__("Do you really want to STOP this Material Request?"));

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Stopped', 'docs': doc}, function(r,rt) {
			cur_frm.refresh();
		});
	}
};

cur_frm.cscript['Unstop Material Request'] = function(){
	var doc = cur_frm.doc;
	var check = confirm(__("Do you really want to UNSTOP this Material Request?"));

	if (check) {
		return $c('runserverobj', args={'method':'update_status', 'arg': 'Submitted','docs': doc}, function(r,rt) {
			cur_frm.refresh();
		});
	}
};

cur_frm.cscript.send_sms = function() {
	frappe.require("assets/erpnext/js/sms_manager.js");
	var sms_man = new SMSManager(cur_frm.doc);
}
