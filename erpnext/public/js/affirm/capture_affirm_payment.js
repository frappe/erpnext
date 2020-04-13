frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        if (!frm.doc.__islocal && frm.doc.affirm_id) {
            frm.add_custom_button(__("Capture Affirm Payment"), function() {
                frappe.call({
                    method: "erpnext.erpnext_integrations.doctype.affirm_settings.affirm_settings.capture_payment",
                    freeze: true,
                    args: {
                        sales_order: frm.doc.name,
                        affirm_id: frm.doc.affirm_id
                    },
                    callback: function(r) {
                        if (!r.exe) {
                            frappe.msgprint("Payment Captured Successfully")
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
    }
});