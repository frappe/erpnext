// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// common partner functions
// =========================


// get sates on country trigger
// -----------------------------
cur_frm.cscript.get_states=function(doc,dt,dn){
   return $c('runserverobj', args={'method':'check_state', 'docs':wn.model.compress(make_doclist(doc.doctype, doc.name))},
    function(r,rt){
      if(r.message) {
        set_field_options('state', r.message);
      }
    }  
  );

}

cur_frm.cscript.country = function(doc, dt, dn) {
  cur_frm.cscript.get_states(doc, dt, dn);
}


// get query select Territory
// ---------------------------
if(cur_frm.fields_dict['territory']){
	cur_frm.fields_dict['territory'].get_query = function(doc,dt,dn) {
		return {
			filters: {
				'is_group': "No" 
			}
		}
	}
}

cur_frm.cscript.render_contact_row = function(wrapper, data) {
	// prepare data
	data.fullname = (data.first_name || '') 
		+ (data.last_name ? ' ' + data.last_name : '');
	data.primary = data.is_primary_contact ? ' [Primary]' : '';
	
	// prepare description
	var description = [];
	$.each([
		['phone', 'Tel'],
		['mobile_no', 'Mobile'],
		['email_id', 'Email'],
		['department', 'Department'],
		['designation', 'Designation']],
		function(i, v) {
			if(v[0] && data[v[0]]) {
				description.push(repl('<h6>%(label)s:</h6> %(value)s', {
					label: v[1],
					value: data[v[0]],
				}));
			}
		});
	data.description = description.join('<br />');
	
	cur_frm.cscript.render_row_in_wrapper(wrapper, data, 'Contact');
}

cur_frm.cscript.render_address_row = function(wrapper, data) {
	// prepare data
	data.fullname = data.address_type;
	data.primary = '';
	if (data.is_primary_address) data.primary += ' [Preferred for Billing]';
	if (data.is_shipping_address) data.primary += ' [Preferred for Shipping]';
	
	// prepare address
	var address = [];
	$.each(['address_line1', 'address_line2', 'city', 'state', 'country', 'pincode'],
		function(i, v) {
			if(data[v]) address.push(data[v]);
		});
	
	data.address = address.join('<br />');
	data.address = "<p class='address-list'>" + data.address + "</p>";
	
	// prepare description
	var description = [];
	$.each([
		['address', 'Address'],
		['phone', 'Tel'],
		['fax', 'Fax'],
		['email_id', 'Email']],
		function(i, v) {
			if(data[v[0]]) {
				description.push(repl('<h6>%(label)s:</h6> %(value)s', {
					label: v[1],
					value: data[v[0]],
				}));
			}
		});
	data.description = description.join('<br />');
	
	cur_frm.cscript.render_row_in_wrapper(wrapper, data, 'Address');
	
	$(wrapper).find('p.address-list').css({
		'padding-left': '10px',
		'margin-bottom': '-10px'
	});
}

cur_frm.cscript.render_row_in_wrapper = function(wrapper, data, doctype) {
	// render
	var $wrapper = $(wrapper);
	
	data.doctype = doctype.toLowerCase();
	
	$wrapper.append(repl("\
		<h4><a class='link_type'>%(fullname)s</a>%(primary)s</h4>\
		<div class='description'>\
			<p>%(description)s</p>\
			<p><a class='delete link_type'>delete this %(doctype)s</a></p>\
		</div>", data));
	
	// make link
	$wrapper.find('h4 a.link_type').click(function() {
		loaddoc(doctype, data.name);
	});
	
	// css
	$wrapper.css({ 'margin': '0px' });
	$wrapper.find('div.description').css({
		'padding': '5px 2px',
		'line-height': '150%',
	});
	$wrapper.find('h6').css({ 'display': 'inline-block' });
	
	// show delete
	var $delete_doc = $wrapper.find('a.delete');
	if (wn.model.can_delete(doctype)) {
		$delete_doc.toggle(true);
	} else {
		$delete_doc.toggle(false);
	}
	$delete_doc.css({
		'padding-left': '0px'
	});

	$delete_doc.click(function() {
		cur_frm.cscript.delete_doc(doctype, data.name);
		return false;
	});
}

cur_frm.cscript.delete_doc = function(doctype, name) {
	// confirm deletion
	var go_ahead = confirm(repl('Delete %(doctype)s "%(name)s"', {
		doctype: doctype,
		name: name
	}));
	if (!go_ahead) return;

	return wn.call({
		method: 'webnotes.model.delete_doc',
		args: {
			dt: doctype,
			dn: name
		},
		callback: function(r) {
			//console.log(r);
			if (!r.exc) {
				// run the correct list
				var list_name = doctype.toLowerCase() + '_list';
				cur_frm[list_name].run();
			}
		}
	});
}

// Render List
cur_frm.cscript.render_list = function(doc, doctype, wrapper, ListView, make_new_doc) {
	wn.model.with_doctype(doctype, function(r) {
		if((r && r['403']) || wn.boot.profile.all_read.indexOf(doctype)===-1) {
			return;
		}
		var RecordListView = wn.views.RecordListView.extend({
			default_docstatus: ['0', '1', '2'],
			default_filters: [
				[doctype, doc.doctype.toLowerCase().replace(" ", "_"), '=', doc.name],
			],
		});
		
		if (make_new_doc) {
			RecordListView = RecordListView.extend({
				make_new_doc: make_new_doc,
			});
		}
		
		var record_list_view = new RecordListView(doctype, wrapper, ListView);
		if (!cur_frm[doctype.toLowerCase().replace(" ", "_") + "_list"]) {
			cur_frm[doctype.toLowerCase().replace(" ", "_") + "_list"] = record_list_view;
		}
	});
}

