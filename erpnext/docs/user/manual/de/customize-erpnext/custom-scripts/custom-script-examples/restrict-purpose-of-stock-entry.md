## 15.3.1.6 Anliegen der Lagerbuchung einschränken

    frappe.ui.form.on("Material Request", "validate", function(frm) {
        if(user=="user1@example.com" && frm.doc.purpose!="Material Receipt") {
            msgprint("You are only allowed Material Receipt");
            throw "Not allowed";
        }
    }

{next}

Contributed by <A HREF="http://www.cwt-kabel.de">CWT connector & wire technology GmbH</A>

<A HREF="http://www.cwt-kabel.de"><IMG alt="logo" src="http://www.cwt-assembly.com/sites/all/images/logo.png" height=100></A>
