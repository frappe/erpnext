/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test'] = {
	add_fields: ["name", "status", "invoiced"],
	filters:[["docstatus","=","0"]],
	get_indicator: function(doc) {
		if(doc.status=="Approved"){
			return [__("Approved"), "green", "status,=,Approved"];
		}
		if(doc.status=="Rejected"){
			return [__("Rejected"), "yellow", "status,=,Rejected"];
		}
	},
	onload: function(listview) {
		listview.page.add_menu_item(__("Create Multiple"), function() {
			create_multiple_dialog(listview);
		});
	}
};

var create_multiple_dialog = function(listview){
	var dialog = new frappe.ui.Dialog({
		title: 'Create Multiple Lab Test',
		width: 100,
		fields: [
			{fieldtype: "Link", label: "Patient", fieldname: "patient", options: "Patient", reqd: 1},
			{fieldtype: "Select", label: "Invoice / Patient Encounter", fieldname: "doctype",
				options: "\nSales Invoice\nPatient Encounter", reqd: 1},
			{fieldtype: "Dynamic Link", fieldname: "docname", options: "doctype", reqd: 1,
				get_query: function(){
					return {
						filters: {
							"patient": dialog.get_value("patient"),
							"docstatus": 1
						}
					};
				}
			}
		],
		primary_action_label: __("Create Lab Test"),
		primary_action : function(){
			frappe.call({
				method: 'erpnext.healthcare.doctype.lab_test.lab_test.create_multiple',
				args:{
					'doctype': dialog.get_value("doctype"),
					'docname': dialog.get_value("docname")
				},
				callback: function(data) {
					if(!data.exc){
						listview.refresh();
					}
				},
				freeze: true,
				freeze_message: "Creating Lab Test..."
			});
			dialog.hide();
		}
	});

	dialog.show();
};
