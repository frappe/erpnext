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

cur_frm.cscript.onload = function(doc, dt, dn) {
	if (!doc.status) doc.status = 'Draft';
	cfn_set_fields(doc, dt, dn);
}

cur_frm.cscript.refresh = function(doc, dt, dn) {
	erpnext.hide_naming_series();
	cur_frm.set_intro("");
	cfn_set_fields(doc, dt, dn);
	if(doc.docstatus===0 && !doc.__islocal) {
		cur_frm.set_intro("Submit this Production Order for further processing.");
	} else if(doc.docstatus===1) {
		if(doc.status === "Stopped") {
			cur_frm.set_intro("This Production Order is Stopped.");
		} else {
			if(doc.produced_qty == doc.qty) {
				cur_frm.set_intro("This Production Order is Completed.");
			} else {
				cur_frm.set_intro("This Production Order is in progress.");
			}
		}
	}
}

var cfn_set_fields = function(doc, dt, dn) {
	if (doc.docstatus == 1) {
		if (doc.status != 'Stopped' && doc.status != 'Completed')
		cur_frm.add_custom_button('Stop!', cur_frm.cscript['Stop Production Order']);
		else if (doc.status == 'Stopped')
			cur_frm.add_custom_button('Unstop', cur_frm.cscript['Unstop Production Order']);

		if (doc.status == 'Submitted' || doc.status == 'Material Transferred' || doc.status == 'In Process'){
			cur_frm.add_custom_button('Transfer Raw Materials', cur_frm.cscript['Transfer Raw Materials']);
			cur_frm.add_custom_button('Update Finished Goods', cur_frm.cscript['Update Finished Goods']);
		} 
	}
}

cur_frm.cscript.production_item = function(doc) {
	cur_frm.call({
		method: "get_item_details",
		args: { item: doc.production_item }
	});
}

cur_frm.cscript['Stop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do you really want to stop production order: " + doc.name);
	if (check) {
		$c_obj(make_doclist(doc.doctype, doc.name), 'stop_unstop', 'Stopped', function(r, rt) {cur_frm.refresh();});
	}
}

cur_frm.cscript['Unstop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm("Do really want to unstop production order: " + doc.name);
	if (check)
			$c_obj(make_doclist(doc.doctype, doc.name), 'stop_unstop', 'Unstopped', function(r, rt) {cur_frm.refresh();});
}

cur_frm.cscript['Transfer Raw Materials'] = function() {
	var doc = cur_frm.doc;
	cur_frm.cscript.make_se(doc, 'Material Transfer');
}

cur_frm.cscript['Update Finished Goods'] = function() {
	var doc = cur_frm.doc;
	cur_frm.cscript.make_se(doc, 'Manufacture/Repack');
}

cur_frm.cscript.make_se = function(doc, purpose) {
	var se = wn.model.get_new_doc("Stock Entry");
	se.purpose = purpose;
	se.production_order = doc.name;
	se.company = doc.company;
	se.fg_completed_qty = doc.qty - doc.produced_qty;
	se.bom_no = doc.bom_no;
	se.use_multi_level_bom = doc.use_multi_level_bom;
	loaddoc('Stock Entry', se.name);
}

cur_frm.fields_dict['production_item'].get_query = function(doc) {
	 return 'SELECT DISTINCT `tabItem`.`name`, `tabItem`.`description` FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` = "0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.docstatus != 2 AND `tabItem`.is_pro_applicable = "Yes" AND `tabItem`.%(key)s LIKE "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return 'SELECT `tabProject`.name FROM `tabProject` \
		WHERE `tabProject`.status not in ("Completed", "Cancelled") \
		AND `tabProject`.name LIKE "%s" ORDER BY `tabProject`.name ASC LIMIT 50';
}


cur_frm.set_query("bom_no", function(doc) {
	if (doc.production_item) {
		return erpnext.queries.bom({item: cstr(doc.production_item)});
	} else msgprint(" Please enter Production Item first");
});