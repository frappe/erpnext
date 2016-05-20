// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.cscript.onload_post_render = function(doc, cdt, cdn) {
	cur_frm.disable_save();
	cur_frm.toolbar.print_icon.addClass("hide");
	return cur_frm.call({
		doc: cur_frm.doc,
		method: 'get_transactions',
		callback: function(r) {
			cur_frm.cscript.update_selects(r);
			cur_frm.cscript.select_doc_for_series(doc, cdt, cdn);
		}
	});
}

cur_frm.cscript.update_selects = function(r) {
	set_field_options('select_doc_for_series', r.message.transactions);
	set_field_options('prefix', r.message.prefixes);
}

cur_frm.cscript.select_doc_for_series = function(doc, cdt, cdn) {
	cur_frm.set_value('user_must_always_select', 0);
	cur_frm.toggle_display(['help_html','set_options', 'user_must_always_select', 'update'],
		doc.select_doc_for_series);

	var callback = function(r, rt){
		locals[cdt][cdn].set_options = r.message;
		refresh_field('set_options');
		if(r.message && r.message.split('\n')[0]=='')
			cur_frm.set_value('user_must_always_select', 1);
	}

	if(doc.select_doc_for_series)
		return $c_obj(doc,'get_options','',callback);
}

cur_frm.cscript.update = function() {
	return cur_frm.call_server('update_series', '', cur_frm.cscript.update_selects);
}

cur_frm.cscript.prefix = function(doc, dt, dn) {
	return cur_frm.call_server('get_current', '', function(r) {
		refresh_field('current_value');
	});
}
