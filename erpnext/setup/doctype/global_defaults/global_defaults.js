// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	validate: function(doc, cdt, cdn) {
		return $c_obj(doc, 'get_defaults', '', function(r, rt){
			sys_defaults = r.message;
		});
	}
});
