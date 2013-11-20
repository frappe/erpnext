// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.toggle_enable('year_start_date', doc.__islocal)
	
	if (!doc.__islocal && (doc.name != sys_defaults.fiscal_year)) {
		cur_frm.add_custom_button(wn._("Set as Default"), cur_frm.cscript.set_as_default);
		cur_frm.set_intro(wn._("To set this Fiscal Year as Deafult, click on 'Set as Default'"));
	} else cur_frm.set_intro("");
}

cur_frm.cscript.set_as_default = function() {
	return wn.call({
		doc: cur_frm.doc,
		method: "set_as_default"
	});
}