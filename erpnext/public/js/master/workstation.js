// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Workstation", {
	onload(frm) {
		if(frm.is_new())
		{
			frappe.call({
				type:"GET",
				method:"erpnext.manufacturing.master.workstation.workstation.get_default_holiday_list",
				callback: function(r) {
					if(!r.exe && r.message){
						frm.set_value("holiday_list", r.message);
					}
				}
			})
		}
	},
});
