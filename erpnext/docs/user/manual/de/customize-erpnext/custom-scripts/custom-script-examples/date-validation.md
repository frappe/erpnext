## 15.3.1.2 Datenvalidierung

	frappe.ui.form.on("Event", "validate", function(frm) {
        if (frm.doc.from_date < get_today()) {
            msgprint(__("You can not select past date in From Date"));
            throw "past date selected"
        }
	});

{next}

Contributed by <A HREF="http://www.cwt-kabel.de">CWT connector & wire technology GmbH</A>

<A HREF="http://www.cwt-kabel.de"><IMG alt="logo" src="http://www.cwt-assembly.com/sites/all/images/logo.png" height=100></A>
