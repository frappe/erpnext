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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

cur_frm.fields_dict['delivery_note'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{ 'docstatus': 0}
	}
}


cur_frm.fields_dict['item_details'].grid.get_field('item_code').get_query = 
		function(doc, cdt, cdn) {
			return {
				query: "stock.doctype.packing_slip.packing_slip.item_details",
				filters:{ 'delivery_note': doc.delivery_note}
			}
}

cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	if(doc.delivery_note && doc.__islocal) {
			cur_frm.cscript.get_items(doc, cdt, cdn);
	}
}

cur_frm.cscript.get_items = function(doc, cdt, cdn) {
	this.frm.call({
		doc: this.frm.doc,
		method: "get_items",
		callback: function(r) {
			if(!r.exc) cur_frm.refresh();
		}
	});
}

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.toggle_display("misc_details", doc.amended_from);
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	cur_frm.cscript.validate_case_nos(doc);
	cur_frm.cscript.validate_calculate_item_details(doc);
}

// To Case No. cannot be less than From Case No.
cur_frm.cscript.validate_case_nos = function(doc) {
	doc = locals[doc.doctype][doc.name];
	if(cint(doc.from_case_no)==0) {
		msgprint("Case No. cannot be 0")
		validated = false;
	} else if(!cint(doc.to_case_no)) {
		doc.to_case_no = doc.from_case_no;
		refresh_field('to_case_no');
	} else if(cint(doc.to_case_no) < cint(doc.from_case_no)) {
		msgprint("'To Case No.' cannot be less than 'From Case No.'");
		validated = false;
	}	
}


cur_frm.cscript.validate_calculate_item_details = function(doc) {
	doc = locals[doc.doctype][doc.name];
	var ps_detail = getchildren('Packing Slip Item', doc.name, 'item_details');

	cur_frm.cscript.validate_duplicate_items(doc, ps_detail);
	cur_frm.cscript.calc_net_total_pkg(doc, ps_detail);
}


// Do not allow duplicate items i.e. items with same item_code
// Also check for 0 qty
cur_frm.cscript.validate_duplicate_items = function(doc, ps_detail) {
	for(var i=0; i<ps_detail.length; i++) {
		for(var j=0; j<ps_detail.length; j++) {
			if(i!=j && ps_detail[i].item_code && ps_detail[i].item_code==ps_detail[j].item_code) {
				msgprint("You have entered duplicate items. Please rectify and try again.");
				validated = false;
				return;
			}
		}
		if(flt(ps_detail[i].qty)<=0) {
			msgprint("Invalid quantity specified for item " + ps_detail[i].item_code +
				". Quantity should be greater than 0.");
			validated = false;
		}
	}
}


// Calculate Net Weight of Package
cur_frm.cscript.calc_net_total_pkg = function(doc, ps_detail) {
	var net_weight_pkg = 0;
	doc.net_weight_uom = ps_detail?ps_detail[0].weight_uom:'';
	doc.gross_weight_uom = doc.net_weight_uom;

	for(var i=0; i<ps_detail.length; i++) {
		var item = ps_detail[i];
		if(item.weight_uom != doc.net_weight_uom) {
			msgprint("Different UOM for items will lead to incorrect \
			(Total) Net Weight value. Make sure that Net Weight of each item is \
			in the same UOM.")
			validated = false;
		}
		net_weight_pkg += flt(item.net_weight) * flt(item.qty);
	}

	doc.net_weight_pkg = roundNumber(net_weight_pkg, 2);
	if(!flt(doc.gross_weight_pkg)) {
		doc.gross_weight_pkg = doc.net_weight_pkg
	}
	refresh_many(['net_weight_pkg', 'net_weight_uom', 'gross_weight_uom', 'gross_weight_pkg']);
}

var make_row = function(title,val,bold){
	var bstart = '<b>'; var bend = '</b>';
	return '<tr><td class="datalabelcell">'+(bold?bstart:'')+title+(bold?bend:'')+'</td>'
	 +'<td class="datainputcell" style="text-align:left;">'+ val +'</td>'
	 +'</tr>'
}

cur_frm.pformat.net_weight_pkg= function(doc){
	return '<table style="width:100%">' + make_row('Net Weight', doc.net_weight_pkg) + '</table>'
}

cur_frm.pformat.gross_weight_pkg= function(doc){
	return '<table style="width:100%">' + make_row('Gross Weight', doc.gross_weight_pkg) + '</table>'
}