/*
(c) ESS 2015-16
*/
frappe.listview_settings['Lab Test'] = {
	add_fields: ["name", "status", "invoice"],
	filters:[["docstatus","=","0"]],
	get_indicator: function(doc) {
		if(doc.status=="Approved"){
        		return [__("Approved"), "green", "status,=,Approved"];
        	}
		if(doc.status=="Rejected"){
        		return [__("Rejected"), "yellow", "status,=,Rejected"];
        	}
	},
	onload: function(me){
		me.page.set_primary_action(__("New"),function(){
			get_from(me)
		},"icon-file-alt");
	}
};

var get_from = function(frm){
	var d = new frappe.ui.Dialog({
		title: __("Get From"),
		fields: [{
				"fieldtype": "Link",
				"label": "Patient",
				"fieldname": "patient",
				"options": "Patient",
				"reqd": 1
			},
			{
				"fieldtype": "Select",
				"label": "From",
				"fieldname": "from",
				"options": ["Sales Invoice","Consultation"],
				"reqd": 1
			},
			{
					"fieldtype": "Dynamic Link",
					"fieldname": "cs",
					"options": "from",
					"reqd": 1
			}
		],
		primary_action_label: __("Create Lab Test"),
		primary_action : function(){
				var values = d.get_values();
				if(!values)
					return;
				if(values["from"]=="Consultation")
					create_test_from_consultation(values["cs"])
				if(values["from"]=="Sales Invoice")
					create_test_from_invoice(values["cs"], values["patient"])
				d.hide();
			}
	})
	d.fields_dict["cs"].get_query = function(txt){
		if(d.get_value("from")=="Consultation"){
			return {
			filters: {
				"patient": d.get_value("patient")
				}
			}
		}else {
			return {
			filters: {
				"docstatus": 1
				}
			}
		};
	}
	d.show();
}

var create_test_from_invoice = function(sale_invoice, patient){
	frappe.call({
		"method": "erpnext.medical.doctype.lab_test.lab_test.create_lab_test_from_invoice",
		"args": {invoice : sale_invoice, patient: patient},
			callback: function (data) {
		if(!data.exc){
			frappe.route_options = {"invoice": sale_invoice}
			frappe.set_route("List", "Lab Test");
		}
			}
	})
}

var create_test_from_consultation = function(consultation){
	frappe.call({
		"method": "erpnext.medical.doctype.lab_test.lab_test.create_lab_test_from_consultation",
		"args": {consultation : consultation},
		callback: function (data) {
			if(!data.exc){
				frappe.route_options = {"docstatus": 0}
				frappe.set_route("List", "Lab Test");
			}
		}
	})
}
