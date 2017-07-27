
    frappe.ui.form.on("Material Request", "validate", function(frm) {
        if(frappe.user=="user1@example.com" && frm.doc.purpose!="Material Receipt") {
            frappe.msgprint("You are only allowed Material Receipt");
            frappe.throw(__("Not allowed"));
        }
    }


{next}
