// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.job_applicant = function() {
	frappe.call({
		doc: cur_frm.doc,
		method: "set_applicant_name",
		callback: function(r) {
			if(!r.exe){
				refresh_field("applicant_name");
			}
		}
	});
}