// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vehicle Request', {
	refresh: function (frm) {
        if(frm.doc.workflow_state == "Waiting MTO Approval" || frm.doc.workflow_state == "Approved"){
            frm.set_df_property('vehicle', 'reqd',  frappe.user.has_role(["ADM User","Branch Manager","Fleet Manager"]))
            frm.set_df_property('kilometer_reading', 'reqd',  frappe.user.has_role(["ADM User","Branch Manager","Fleet Manager"]))
            frm.toggle_display("fleet_details_section", frappe.user.has_role(["Fleet Manager","System Manager"]));
            frm.refresh_fields();
        }
        else{
            cur_frm.toggle_display("fleet_details_section", false);
        }
        if (frm.doc.docstatus == 1 ){
            open_extension(frm)
        }
    },

	setup: function (frm) {
        frm.get_field('items').grid.editable_fields = [
            { fieldname: 'employee', columns: 2 },
            { fieldname: 'employee_name', columns: 2 },
            { fieldname: 'designation', columns: 2 },
            { fieldname: 'division', columns: 3 },
        ];
        frappe.form.link_formatters['Employee'] = function(value) {
                return value;
        }
    },
    from_date: function(frm){
        get_date(frm);
    },
    to_date: function(frm){
        check_date(frm);
    },

    vehicle: function(frm){
        get_previous_km(frm)
    },
    
	onload:function(frm){
		frm.set_query('vehicle', () => {
			return {
				filters: {
					equipment_type: frm.doc.vehicle_type,
                    hired_equipment: 0
				}
			}
		})
	}
});

function open_extension(frm){
    frm.add_custom_button('Extend', () => {
        frappe.model.open_mapped_doc({
            method: "erpnext.fleet_management.doctype.vehicle_request.vehicle_request.create_vr_extension",	
            frm: cur_frm
        });
    })
}

function get_date(frm){
    var get_date = cur_frm.doc.from_date;
    frappe.model.set_value("time_of_departure", get_date);

}

function check_date(frm){
    frappe.call({
        method:"erpnext.fleet_management.doctype.vehicle_request.vehicle_request.check_form_date_and_to_date",
        args: {
            'from_date': frm.doc.from_date,
            'to_date': frm.doc.to_date
        },
    });
}

function get_previous_km(frm){
    frappe.call({
        method: "erpnext.fleet_management.doctype.vehicle_request.vehicle_request.get_previous_km",
        args: {
        'vehicle': frm.doc.vehicle,
        'vehicle_number': frm.doc.vehicle_number,
    },
    callback: function(r){
            console.log(r.message)
            cur_frm.set_value("previous_km", r.message[0].km)
        }
    });
}