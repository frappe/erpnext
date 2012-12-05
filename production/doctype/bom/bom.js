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
}


// Triggers
//--------------------------------------------------------------------------------------------------
cur_frm.cscript.item = function(doc, dt, dn) {
	if (doc.item) {
		get_server_fields('get_item_detail',doc.item,'',doc,dt,dn,1);
	}
}


cur_frm.cscript.workstation = function(doc,dt,dn) {
	var d = locals[dt][dn];
	if (d.workstation) {
		var callback = function(r, rt) {
			calculate_op_cost(doc, dt, dn);
			calculate_total(doc);
		}
		get_server_fields('get_workstation_details',d.workstation,'bom_operations',doc,dt,dn,1, callback);
	}
}


cur_frm.cscript.hour_rate = function(doc, dt, dn) {
	calculate_op_cost(doc, dt, dn);
	calculate_total(doc);
}


cur_frm.cscript.time_in_mins = cur_frm.cscript.hour_rate;


cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn);
}


cur_frm.cscript.bom_no	= function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn);
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
				calculate_rm_cost(doc, cdt, cdn);
				calculate_total(doc);
			},
			freeze: true
		});
	}
}


cur_frm.cscript.qty = function(doc, cdt, cdn) {
	calculate_rm_cost(doc, cdt, cdn);
	calculate_total(doc);
}


cur_frm.cscript.rate = cur_frm.cscript.qty;


cur_frm.cscript.is_default = function(doc, cdt, cdn) {
	if (doc.docstatus == 1)
		$c_obj(make_doclist(cdt, cdn), 'manage_default_bom', '', '');
}


cur_frm.cscript.is_active = function(doc, dt, dn) {
	if (!doc.__islocal)
		$c_obj(make_doclist(dt, dn), 'manage_active_bom', '', '');
}


// Calculate Operating Cost
var calculate_op_cost = function(doc, dt, dn) {	
	var op = getchildren('BOM Operation', doc.name, 'bom_operations');
	total_op_cost = 0;
	for(var i=0;i<op.length;i++) {
		op_cost =	flt(op[i].hour_rate) * flt(op[i].time_in_mins) / 60;
		set_multiple('BOM Operation',op[i].name, {'operating_cost': op_cost}, 'bom_operations');
		total_op_cost += op_cost;
	}
	doc.operating_cost = total_op_cost;
	refresh_field('operating_cost');
}


// Calculate Raw Material Cost
var calculate_rm_cost = function(doc, dt, dn) {	
	var rm = getchildren('BOM Item', doc.name, 'bom_materials');
	total_rm_cost = 0;
	for(var i=0;i<rm.length;i++) {
		amt =	flt(rm[i].rate) * flt(rm[i].qty);
		set_multiple('BOM Item',rm[i].name, {'amount': amt}, 'bom_materials');
		set_multiple('BOM Item',rm[i].name, {'qty_consumed_per_unit': flt(rm[i].qty)/flt(doc.quantity)}, 'bom_materials');
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
	return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.description FROM `tabItem` WHERE is_manufactured_item = "Yes" and (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.`%(key)s` like "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return 'SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}

cur_frm.fields_dict['bom_materials'].grid.get_field('item_code').get_query = function(doc) {
	return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.description FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.`%(key)s` like "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

cur_frm.fields_dict['bom_materials'].grid.get_field('bom_no').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	return 'SELECT DISTINCT `tabBOM`.`name`, `tabBOM`.`remarks` FROM `tabBOM` WHERE `tabBOM`.`item` = "' + d.item_code + '" AND `tabBOM`.`is_active` = "Yes" AND `tabBOM`.docstatus = 1 AND `tabBOM`.`name` like "%s" ORDER BY `tabBOM`.`name` LIMIT 50';
}

cur_frm.cscript.validate = function(doc, dt, dn) {
	calculate_op_cost(doc, dt, dn);
	calculate_rm_cost(doc, dt, dn);
	calculate_total(doc);
}
