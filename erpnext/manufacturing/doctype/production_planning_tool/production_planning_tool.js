// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt



cur_frm.cscript.onload = function(doc) {
	cur_frm.set_value("company", frappe.defaults.get_user_default("Company"))
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

cur_frm.add_fetch("material_request", "transaction_date", "material_request_date");

cur_frm.add_fetch("sales_order", "transaction_date", "sales_order_date");
cur_frm.add_fetch("sales_order", "customer", "customer");
cur_frm.add_fetch("sales_order", "base_grand_total", "grand_total");

frappe.ui.form.on("Production Planning Tool", {
	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "planned_qty");
	},
	get_sales_orders: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_open_sales_orders",
			callback: function(r) {
				refresh_field("sales_orders");
			}
		});
	},
	
	get_material_request: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_pending_material_requests",
			callback: function(r) {
				refresh_field("material_requests");
			}
		});
	},
	
	get_items: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_items",
			callback: function(r) {
				refresh_field("items");
			}
		});
	},
	
	create_production_order: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "raise_production_orders"
		});
	},
	
	create_material_requests: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "raise_material_requests"
		});
	}
});

cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_order.production_order.get_item_details",
			args: {
				"item" : d.item_code
			},
			callback: function(r) {
				$.extend(d, r.message);
				refresh_field("items");
			}
		});
	}
}

cur_frm.cscript.download_materials_required = function(doc, cdt, cdn) {
	return $c_obj(doc, 'validate_data', '', function(r, rt) {
		if (!r['exc'])
			$c_obj_csv(doc, 'download_raw_materials', '', '');
	});
}

cur_frm.fields_dict['sales_orders'].grid.get_field('sales_order').get_query = function(doc) {
	var args = { "docstatus": 1 };
	if(doc.customer) {
		args["customer"] = doc.customer;
	}

	return { filters: args }
}

cur_frm.fields_dict['items'].grid.get_field('item_code').get_query = function(doc) {
	return erpnext.queries.item({
		'is_stock_item': 1
	});
}

cur_frm.fields_dict['items'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return {
			query: "erpnext.controllers.queries.bom",
			filters:{'item': cstr(d.item_code)}
		}
	} else frappe.msgprint(__("Please enter Item first"));
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.customer_query"
	}
}

cur_frm.fields_dict.sales_orders.grid.get_field("customer").get_query =
	cur_frm.fields_dict.customer.get_query;

cur_frm.cscript.planned_start_date = function(doc, cdt, cdn) {
	erpnext.utils.copy_value_in_all_row(doc, cdt, cdn, "items", "planned_start_date");
}
