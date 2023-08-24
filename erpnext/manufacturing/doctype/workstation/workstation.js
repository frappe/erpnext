// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Workstation", {
	onload(frm) {
		if(frm.is_new())
		{
			frappe.call({
				type:"GET",
				method:"erpnext.manufacturing.doctype.workstation.workstation.get_default_holiday_list",
				callback: function(r) {
					if(!r.exe && r.message){
						cur_frm.set_value("holiday_list", r.message);
					}
				}
			})
		}
	},

	workstation_type(frm) {
		if (frm.doc.workstation_type) {
			frm.call({
				method: "set_data_based_on_workstation_type",
				doc: frm.doc,
				callback: function(r) {
					frm.refresh_fields();
				}
			})
		}
	}
});

frappe.tour['Workstation'] = [
	{
		fieldname: "workstation_name",
		title: "Workstation Name",
		description: __("You can set it as a machine name or operation type. For example, stiching machine 12")
	},
	{
		fieldname: "production_capacity",
		title: "Production Capacity",
		description: __("No. of parallel job cards which can be allowed on this workstation. Example: 2 would mean this workstation can process production for two Work Orders at a time.")
	},
	{
		fieldname: "holiday_list",
		title: "Holiday List",
		description: __("A Holiday List can be added to exclude counting these days for the Workstation.")
	},
	{
		fieldname: "working_hours",
		title: "Working Hours",
		description: __("Under Working Hours table, you can add start and end times for a Workstation. For example, a Workstation may be active from 9 am to 1 pm, then 2 pm to 5 pm. You can also specify the working hours based on shifts. While scheduling a Work Order, the system will check for the availability of the Workstation based on the working hours specified.")
	},


];
