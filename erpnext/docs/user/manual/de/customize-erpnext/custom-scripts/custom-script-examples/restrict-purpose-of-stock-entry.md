# Anliegen der Lagerbuchung einschränken
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

    frappe.ui.form.on("Material Request", "validate", function(frm) {
        if(user=="user1@example.com" && frm.doc.purpose!="Material Receipt") {
            frappe.msgprint("You are only allowed Material Receipt");
            frappe.throw(__("Not allowed"));
        }
    }

{next}
