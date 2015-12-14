## 15.3.1.6 Anliegen der Lagerbuchung einschränken

    frappe.ui.form.on("Material Request", "validate", function(frm) {
        if(user=="user1@example.com" && frm.doc.purpose!="Material Receipt") {
            msgprint("You are only allowed Material Receipt");
            throw "Not allowed";
        }
    }

{next}
