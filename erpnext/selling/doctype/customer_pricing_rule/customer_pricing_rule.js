// Copyright (c) 2021, Sangita and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer Pricing Rule', {
	setup:function(frm){
		$.each(["item_details"], function(i, table_fieldname) {
			frm.get_field(table_fieldname).grid.editable_fields = [
				{fieldname: 'item', columns: 4},
				{fieldname: 'item_name', columns: 4},
				{fieldname: 'base_price', columns: 4},
				{fieldname: 'type', columns: 4},
				{fieldname: 'discount_margin', columns: 4},
				{fieldname: 'list_price', columns: 4}
			];
		});
	},
	after_save: function(frm){
		frappe.call({
			method: 'erpnext.selling.doctype.customer_pricing_rule.customer_pricing_rule.insert_link_to_doc',
			args: {
				'name': frm.doc.name,
				'customer': frm.doc.customer,
				'item_line': frm.doc.item_details
			},
			callback: function(resp){
				// 
			}
		})
	},
	before_load:function(frm){
		var df = frappe.meta.get_docfield("Customer Pricing Rule Item","additional_price",frm.doc.name);
		df.read_only = 1;
		frm.refresh_fields();
	}
});

frappe.ui.form.on("Customer Pricing Rule Item", {
    item: function (frm, cdt, cdn) {
	frm.doc.for_price_list === undefined ? frappe.throw("Please select price list first") : null
	var item = frappe.model.get_value(cdt, cdn, "item");
	var additional_price = frappe.model.get_value(cdt, cdn, "additional_price");
	frappe.db.get_value("Item Price", {"item_code": item, 'price_list':frm.doc.for_price_list}, "price_list_rate", r => {
		frappe.model.set_value(cdt, cdn, "base_price", r.price_list_rate)
	})
	frappe.call({
		method: "erpnext.selling.doctype.customer_pricing_rule.customer_pricing_rule.check_duplicate_item",
		//doc: frm.doc,
		args: {'item':item,'doc':frm.doc},
		callback: function(frm){
			//frappe.validated = false
		}
	})
	},
	additional_price: function(frm,cdt,cdn){
		var item = frappe.model.get_value(cdt, cdn, "item");
		var additional_price = frappe.model.get_value(cdt, cdn, "additional_price");
		
		frappe.db.get_value("Item Price", {"item_code": item, 'price_list':frm.doc.for_price_list}, "price_list_rate", r => {
		let list_price = r.price_list_rate + additional_price
		frappe.model.set_value(cdt, cdn, "list_price", list_price)
		})
		
		// code to clear customer pricing rule link in pricing rule
		frappe.call({
			method: "erpnext.selling.doctype.customer_pricing_rule.customer_pricing_rule.clear_link",
			args: {
				"item": item,
				"customer": frm.doc.customer
			},
			callback: function(resp){
				//
			}
		})
	},
	discount_margin:function(frm,cdt,cdn){
		var d = locals[cdt][cdn]
		if(d.type === "Discount"){
			frappe.model.set_value(cdt,cdn,"additional_price",(d.discount_margin*-1))
		}
		if(d.type === "Margin"){
			frappe.model.set_value(cdt,cdn,"additional_price",(d.discount_margin))
		}
	}

});