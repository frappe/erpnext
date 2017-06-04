frappe.listview_settings['Attendance'] = {
	add_fields: ["status", "attendance_date"],
	get_indicator: function(doc) {
		return [__(doc.status), doc.status=="Present" ? "green" : "darkgrey", "status,=," + doc.status];
	},
onload: function(listview) {
		listview.page.add_menu_item(__("Import Day Attendance Records"), function() {
			frappe.call({
				method: "erpnext.hr.doctype.attendance.attendance.get_from_clock",
				callback: function(r) {
					if (r.message =="No Data")
					{
						msgprint(__("No Data Found"));
					}
					else 
					{
						msgprint(__("Attendance Imported Sucsesfuly"));
					}
						console.log(r.message);
				}
			})
		});

	}
};

