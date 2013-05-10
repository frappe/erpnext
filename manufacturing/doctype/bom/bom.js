// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

// On REFRESH
cur_frm.cscript.refresh = function(doc,dt,dn){
	cur_frm.toggle_enable("item", doc.__islocal);
	
	if (!doc.__islocal && doc.docstatus==0) {
		cur_frm.set_intro("Submit the BOM to use it for manufacturing or repacking.");
	} else cur_frm.set_intro("");
	
	cur_frm.cscript.with_operations(doc);
	set_operation_no(doc);
}

cur_frm.cscript.with_operations = function(doc) {
	cur_frm.fields_dict["bom_materials"].grid.set_column_disp("operation_no", doc.with_operations);
	cur_frm.fields_dict["bom_materials"].grid.toggle_reqd("operation_no", doc.with_operations)
}

cur_frm.cscript.operation_no = function(doc, cdt, cdn) {
	var child = locals[cdt][cdn];
	if(child.parentfield=="bom_operations") set_operation_no(doc);
}

var set_operation_no = function(doc) {
	var op_table = getchildren('BOM Operation', doc.name, 'bom_operations');
	var operations = [];

	for (var i=0, j=op_table.length; i<j; i++) {
		var op = op_table[i].operation_no;
		if (op && !inList(operations, op)) operations.push(op);
	}
	
	cur_frm.fields_dict["bom_materials"].grid.get_field("operation_no")
		.df.options = operations.join("\n");
	
	$.each(getchildren("BOM Item", doc.name, "bom_materials"), function(i, v) {
		if(!inList(operations, cstr(v.operation_no))) v.operation_no = null;
	});
	
	refresh_field("bom_materials");
}

cur_frm.fields_dict["bom_operations"].grid.on_row_delete = function(cdt, cdn){
	set_operation_no(doc);
}

cur_frm.add_fetch("item", "description", "description");
cur_frm.add_fetch("item", "stock_uom", "uom");

cur_frm.cscript.workstation = function(doc,dt,dn) {
	var d = locals[dt][dn];
	wn.model.with_doc("Workstation", d.workstation, function(i, r) {
		d.hour_rate = r.docs[0].hour_rate;
		refresh_field("hour_rate", dn, "bom_operations");
		calculate_op_cost(doc);
		calculate_total(doc);
	});
}


cur_frm.cscript.hour_rate = function(doc, dt, dn) {
	calculate_op_cost(doc);
	calculate_total(doc);
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
		wn.call({
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
				calculate_rm_cost(doc);
				calculate_total(doc);
			},
			freeze: true
		});
	}
}


cur_frm.cscript.qty = function(doc, cdt, cdn) {
	calculate_rm_cost(doc);
	calculate_total(doc);
}

cur_frm.cscript.rate = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.bom_no) {
		msgprint("You can not change rate if BOM mentioned agianst any item");
		get_bom_material_detail(doc, cdt, cdn);
	} else {
		calculate_rm_cost(doc);
		calculate_total(doc);
	}
}

var calculate_op_cost = function(doc) {	
	var op = getchildren('BOM Operation', doc.name, 'bom_operations');
	total_op_cost = 0;
	for(var i=0;i<op.length;i++) {
		op_cost =	flt(flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60, 2);
		set_multiple('BOM Operation',op[i].name, {'operating_cost': op_cost}, 'bom_operations');
		total_op_cost += op_cost;
	}
	doc.operating_cost = total_op_cost;
	refresh_field('operating_cost');
}

var calculate_rm_cost = function(doc) {	
	var rm = getchildren('BOM Item', doc.name, 'bom_materials');
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
var calculate_total = function(doc) {
	doc.total_cost = flt(doc.raw_material_cost) + flt(doc.operating_cost);
	refresh_field('total_cost');
}


cur_frm.fields_dict['item'].get_query = function(doc) {
	return erpnext.queries.item({
		'ifnull(tabItem.is_manufactured_item, "No")': 'Yes',
	})
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return 'SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}

cur_frm.fields_dict['bom_materials'].grid.get_field('item_code').get_query = function(doc) {
	return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.description FROM `tabItem` \
		WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" \
			OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.`%(key)s` like "%s" \
		ORDER BY `tabItem`.`name` LIMIT 50';
}

cur_frm.fields_dict['bom_materials'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return 'SELECT DISTINCT `tabBOM`.`name`, `tabBOM`.`remarks` FROM `tabBOM` \
		WHERE `tabBOM`.`item` = "' + d.item_code + '" AND `tabBOM`.`is_active` = 1 AND \
		 	`tabBOM`.docstatus = 1 AND `tabBOM`.`name` like "%s" \
		ORDER BY `tabBOM`.`name` LIMIT 50';
}

cur_frm.cscript.validate = function(doc, dt, dn) {
	calculate_op_cost(doc);
	calculate_rm_cost(doc);
	calculate_total(doc);
}
