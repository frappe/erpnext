frappe.ui.form.on("Issue", {
	"onload": function(frm) {
		frm.email_field = "raised_by";
	},

	"refresh": function(frm) {
		last_status = frm.doc.status;
	},
	"status": function(frm) {dialog(frm)}
});
function dialog(frm){
    var d = new frappe.ui.Dialog({
                    title: __("Details for "+ frm.doc.status),
                    fields: [
                        {
                            "fieldtype": "Text",
                            "label": __("Resolution Details"),
                            "reqd": 1,
			    "name":"resolution_details"
                        }
                    ]
                });
                
                d.set_value("resolution_details",cur_frm.doc.resolution_details)
                d.set_primary_action(__("Update"), function() {
                    if (d.get_value("resolution_details")===""){
                        show_alert("Resolution Details are Required",5)
                        return
                    }
                    cur_frm.doc.resolution_details = d.get_value("resolution_details")
                    frappe.call({
                        method: 'create_resolution',
                        doc: cur_frm.doc,
			            args:{
				            "text": d.get_value("resolution_details")
			            },
                        callback: function(frm){
                            d.hide();
                            cur_frm.save()
                            cur_frm.refresh()
                        }
                    })
                });
                d.show();
}
