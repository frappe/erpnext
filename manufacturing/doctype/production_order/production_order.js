// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, dt, dn) {
	if (!doc.status) doc.status = 'Draft';
	cfn_set_fields(doc, dt, dn);
}

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.dashboard.reset();
	erpnext.hide_naming_series();
	cur_frm.set_intro("");
	cfn_set_fields(doc, dt, dn);

	if(doc.docstatus===0 && !doc.__islocal) {
		cur_frm.set_intro(wn._("Submit this Production Order for further processing."));
	} else if(doc.docstatus===1) {
		var percent = flt(doc.produced_qty) / flt(doc.qty) * 100;
		cur_frm.dashboard.add_progress(cint(percent) + "% " + wn._("Complete"), percent);

		if(doc.status === "Stopped") {
			cur_frm.dashboard.set_headline_alert(wn._("Stopped"), "alert-danger", "icon-stop");
		}
	}
}

var cfn_set_fields = function(doc, dt, dn) {
	if (doc.docstatus == 1) {
		if (doc.status != 'Stopped' && doc.status != 'Completed')
		cur_frm.add_custom_button(wn._('Stop!'), cur_frm.cscript['Stop Production Order'], "icon-exclamation");
		else if (doc.status == 'Stopped')
			cur_frm.add_custom_button(wn._('Unstop'), cur_frm.cscript['Unstop Production Order'], "icon-check");

		if (doc.status == 'Submitted' || doc.status == 'Material Transferred' || doc.status == 'In Process'){
			cur_frm.add_custom_button(wn._('Transfer Raw Materials'), cur_frm.cscript['Transfer Raw Materials']);
			cur_frm.add_custom_button(wn._('Update Finished Goods'), cur_frm.cscript['Update Finished Goods']);
		} 
	}
}

cur_frm.cscript.production_item = function(doc) {
	return cur_frm.call({
		method: "get_item_details",
		args: { item: doc.production_item }
	});
}

cur_frm.cscript['Stop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(wn._("Do you really want to stop production order: " + doc.name));
	if (check) {
		return $c_obj(make_doclist(doc.doctype, doc.name), 'stop_unstop', 'Stopped', function(r, rt) {cur_frm.refresh();});
	}
}

cur_frm.cscript['Unstop Production Order'] = function() {
	var doc = cur_frm.doc;
	var check = confirm(wn._("Do really want to unstop production order: " + doc.name));
	if (check)
			return $c_obj(make_doclist(doc.doctype, doc.name), 'stop_unstop', 'Unstopped', function(r, rt) {cur_frm.refresh();});
}

cur_frm.cscript['Transfer Raw Materials'] = function() {
	cur_frm.cscript.make_se('Material Transfer');
}

cur_frm.cscript['Update Finished Goods'] = function() {
	cur_frm.cscript.make_se('Manufacture/Repack');
}

cur_frm.cscript.make_se = function(purpose) {
	wn.call({
		method:"manufacturing.doctype.production_order.production_order.make_stock_entry",
		args: {
			"production_order_id": cur_frm.doc.name,
			"purpose": purpose
		},
		callback: function(r) {
			var doclist = wn.model.sync(r.message);
			wn.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	})
}

cur_frm.fields_dict['production_item'].get_query = function(doc) {
	return {
		filters:[
			['Item', 'is_pro_applicable', '=', 'Yes']
		]
	}
}

cur_frm.fields_dict['project_name'].get_query = function(doc, dt, dn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}	
}


cur_frm.set_query("bom_no", function(doc) {
	if (doc.production_item) {
		return{
			query:"controllers.queries.bom",
			filters: {item: cstr(doc.production_item)}
		}
	} else msgprint(wn._("Please enter Production Item first"));
});