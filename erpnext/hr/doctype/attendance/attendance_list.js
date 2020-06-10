frappe.listview_settings['Attendance'] = {
	add_fields: ["status", "attendance_date"],
	get_indicator: function (doc) {
		if (["Present", "Work From Home"].includes(doc.status)) {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Absent", "On Leave"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	},
	onload: function(list_view) {
		let me = this;
		const months = moment.months()
		list_view.page.add_inner_button( __("Mark Attendance"), function(){
			let dialog = new frappe.ui.Dialog({
				title: __("Mark Attendance"),
				fields: [
					{
						fieldname: 'employee',
						label: __('For Employee'),
						fieldtype: 'Link',
						options: 'Employee',
						reqd: 1,
						onchange: function(){
							dialog.set_df_property("unmarked_days", "hidden", 1);
							dialog.set_df_property("status", "hidden", 1);
							dialog.set_df_property("month", "value", '');
							dialog.set_df_property("unmarked_days", "options", []);
						}
					},
					{
						label: __("For Month"),
						fieldtype: "Select",
						fieldname: "month",
						options: months,
						reqd: 1,
						onchange: function(){
							if(dialog.fields_dict.employee.value && dialog.fields_dict.month.value) {
								dialog.set_df_property("status", "hidden", 0);
								dialog.set_df_property("unmarked_days", "options", []);
								me.get_multi_select_options(dialog.fields_dict.employee.value, dialog.fields_dict.month.value).then(options =>{
									dialog.set_df_property("unmarked_days", "hidden", 0);
									dialog.set_df_property("unmarked_days", "options", options);
								});
							}
						}
					},
					{
						label: __("Status"),
						fieldtype: "Select",
						fieldname: "status",
						options: ["Present", "Absent", "Half Day", "Work From Home"],
						hidden:1,
						reqd: 1,

					},
					{
						label: __("Unmarked Attendance for days"),
						fieldname: "unmarked_days",
						fieldtype: "MultiCheck",
						options: [],
						columns: 2,
						hidden: 1
					},
				],
				primary_action(data){
					frappe.confirm(__('Mark attendance as <b>' + data.status + '</b> for <b>' + data.month +'</b>' + ' on selected dates?'), () => {
						frappe.call({
							method: "erpnext.hr.doctype.attendance.attendance.mark_bulk_attendance",
							args: {
								data : data
							},
							callback: function(r) {
								if(r.message === 1) {
									frappe.show_alert({message:__("Attendance Marked"), indicator:'blue'});
									cur_dialog.hide();
								}
							}
						});
					});
					dialog.hide();
					list_view.refresh();
				},
				primary_action_label: __('Mark Attendance')

			});
			dialog.show();
		});
	},
	get_multi_select_options: function(employee, month){
		return new Promise(resolve => {
			frappe.call({
				method: 'erpnext.hr.doctype.attendance.attendance.get_unmarked_days',
				async: false,
				args:{
					employee: employee,
					month: month,
				}
			}).then(r => {
				var options = [];
				for(var d in r.message){
					var momentObj = moment(r.message[d], 'YYYY-MM-DD');
					var date = momentObj.format('DD-MM-YYYY');
					options.push({ "label":date, "value": r.message[d] , "checked": 1});
				}
				resolve(options);
			});
		});
	}
};
