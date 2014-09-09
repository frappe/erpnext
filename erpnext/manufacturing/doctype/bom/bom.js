// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// On REFRESH
frappe.provide("erpnext.bom");
cur_frm.cscript.refresh = function(doc,dt,dn){
	cur_frm.toggle_enable("item", doc.__islocal);

	if (!doc.__islocal && doc.docstatus<2) {
		cur_frm.add_custom_button(__("Update Cost"), cur_frm.cscript.update_cost,
			"icon-money", "btn-default");
	}

	cur_frm.cscript.with_operations(doc);
	erpnext.bom.set_operation_no(doc);
}

cur_frm.cscript.update_cost = function() {
	return frappe.call({
		doc: cur_frm.doc,
		method: "update_cost",
		callback: function(r) {
			if(!r.exc) cur_frm.refresh_fields();
		}
	})
}

cur_frm.cscript.with_operations = function(doc) {
	cur_frm.fields_dict["bom_materials"].grid.set_column_disp("operation_no", doc.with_operations);
	cur_frm.fields_dict["bom_materials"].grid.toggle_reqd("operation_no", doc.with_operations);
}

cur_frm.cscript.operation_no = function(doc, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.parentfield=="bom_operations") erpnext.bom.set_operation_no(doc);
}

erpnext.bom.set_operation_no = function(doc) {
	var op_table = doc.bom_operations || [];
	var operations = [];

	for (var i=0, j=op_table.length; i<j; i++) {
		var op = op_table[i].operation_no;
		if (op && !inList(operations, op)) operations.push(op);
	}

	frappe.meta.get_docfield("BOM Item", "operation_no",
		cur_frm.docname).options = operations.join("\n");

	$.each(doc.bom_materials || [], function(i, v) {
		if(!inList(operations, cstr(v.operation_no))) v.operation_no = null;
	});

	refresh_field("bom_materials");
}

cur_frm.cscript.bom_operations_remove = function(){
	erpnext.bom.set_operation_no(doc);
}

cur_frm.add_fetch("item", "description", "description");
cur_frm.add_fetch("item", "stock_uom", "uom");

cur_frm.cscript.workstation = function(doc,dt,dn) {
	var d = locals[dt][dn];
	frappe.model.with_doc("Workstation", d.workstation, function(name, r) {
		d.hour_rate = r.docs[0].hour_rate;
		refresh_field("hour_rate", dn, "bom_operations");
		erpnext.bom.calculate_op_cost(doc);
		erpnext.bom.calculate_total(doc);
	});
}


cur_frm.cscript.hour_rate = function(doc, dt, dn) {
	erpnext.bom.calculate_op_cost(doc);
	erpnext.bom.calculate_total(doc);
}


cur_frm.cscript.time_in_mins = cur_frm.cscript.hour_rate;

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn);
}

cur_frm.cscript.bom_no	= function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn);
}

cur_frm.cscript.is_default = function(doc) {
	if (doc.is_default) cur_frm.set_value("is_active", 1);
}

var get_bom_material_detail= function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			doc: cur_frm.doc,
			method: "get_bom_material_detail",
			args: {
				'item_code': d.item_code,
				'bom_no': d.bom_no != null ? d.bom_no: '',
				'qty': d.qty
			},
			callback: function(r) {
				d = locals[cdt][cdn];
				$.extend(d, r.message);
				refresh_field("bom_materials");
				doc = locals[doc.doctype][doc.name];
				erpnext.bom.calculate_rm_cost(doc);
				erpnext.bom.calculate_total(doc);
			},
			freeze: true
		});
	}
}


cur_frm.cscript.qty = function(doc, cdt, cdn) {
	erpnext.bom.calculate_rm_cost(doc);
	erpnext.bom.calculate_total(doc);
}

cur_frm.cscript.rate = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.bom_no) {
		msgprint(__("You can not change rate if BOM mentioned agianst any item"));
		get_bom_material_detail(doc, cdt, cdn);
	} else {
		erpnext.bom.calculate_rm_cost(doc);
		erpnext.bom.calculate_total(doc);
	}
}

erpnext.bom.calculate_op_cost = function(doc) {
	var op = doc.bom_operations || [];
	total_op_cost = 0;
	for(var i=0;i<op.length;i++) {
		op_cost =	flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
		set_multiple('BOM Operation',op[i].name, {'operating_cost': op_cost}, 'bom_operations');
		total_op_cost += op_cost;
	}
	doc.operating_cost = total_op_cost;
	refresh_field('operating_cost');
}

erpnext.bom.calculate_rm_cost = function(doc) {
	var rm = doc.bom_materials || [];
	total_rm_cost = 0;
	for(var i=0;i<rm.length;i++) {
		amt =	flt(rm[i].rate) * flt(rm[i].qty);
		set_multiple('BOM Item',rm[i].name, {'amount': amt}, 'bom_materials');
		set_multiple('BOM Item',rm[i].name,
			{'qty_consumed_per_unit': flt(rm[i].qty)/flt(doc.quantity)}, 'bom_materials');
		total_rm_cost += amt;
	}
	doc.raw_material_cost = total_rm_cost;
	refresh_field('raw_material_cost');
}


// Calculate Total Cost
erpnext.bom.calculate_total = function(doc) {
	doc.total_cost = flt(doc.raw_material_cost) + flt(doc.operating_cost);
	refresh_field('total_cost');
}


cur_frm.fields_dict['item'].get_query = function(doc) {
 	return{
		query: "erpnext.controllers.queries.item_query",
		filters:{
			'is_manufactured_item': 'Yes'
		}
	}
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.fields_dict['bom_materials'].grid.get_field('item_code').get_query = function(doc) {
	return{
		query: "erpnext.controllers.queries.item_query"
	}
}

cur_frm.fields_dict['bom_materials'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return{
		filters:{
			'item': d.item_code,
			'is_active': 1,
			'docstatus': 1
		}
	}
}

cur_frm.cscript.validate = function(doc, dt, dn) {
	erpnext.bom.calculate_op_cost(doc);
	erpnext.bom.calculate_rm_cost(doc);
	erpnext.bom.calculate_total(doc);
}
