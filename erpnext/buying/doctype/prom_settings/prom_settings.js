// Copyright (c) 2023, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Prom Settings", {
	
    refresh: function(frm) {
        frm.add_custom_button('Show Import Status', function() {
            frappe.set_route("List", "Prom Import Status");
        })},
	import_prom_prod: function(frm){
        frappe.call({
            method: "erpnext.buying.doctype.prom_integ.prom_to_erp_prod.main",
            freeze: true,
            freeze_message: "Fetching products",
            callback: function(resp) {
                console.log(resp.message)
                if (resp.message === 1){
                    frappe.show_alert({
                    message:__("Some item's won't be imported!"),
                    indicator:"orange"
                    }, 5);
                }
                if (resp.message === 0){
                    frappe.show_alert({
                        message:__("Successful import"),
                        indicator:"green"
                    }, 4);
                }
                
            }
        });
	},

	get_order: function(frm) {
        
		frappe.call({
            method: "erpnext.buying.doctype.prom_integ.orders_get.main", 
            freeze: true,
            freeze_message: "Fetching order"
        });
        
	},

	export_prom_prod: function(frm) {
	    frappe.call({
            method: "erpnext.buying.doctype.prom_integ.erp_to_prom_prod.run",
            freeze: true,
            freeze_message: "Sending products",
            callback: function(resp) {
                if (resp.message === 1){
                    frappe.show_alert({
                    message:__("Export is not avalible! Please try later"),
                    indicator:"red"
                    }, 5);
                }
                if (resp.message === 0){
                    frappe.show_alert({
                        message:__("Processing import"),
                        indicator:"green"
                    }, 4);
                }
                if (resp.message === 2){
                    frappe.show_alert({
                        message:__("No response!"),
                        indicator:"yellow"
                    }, 4);
                }
            }
        });
	}
})