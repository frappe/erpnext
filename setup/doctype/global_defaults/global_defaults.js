// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

// Validate
cur_frm.cscript.validate = function(doc, cdt, cdn) {
	return $c_obj(make_doclist(cdt, cdn), 'get_defaults', '', function(r, rt){
		sys_defaults = r.message;
	});
}