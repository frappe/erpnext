// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'controllers/js/contact_address_common.js' %};

frappe.ui.form.on("Contact", "validate", function(frm) {
	// clear linked customer / supplier / sales partner on saving...
	$.each(["Customer", "Supplier", "Sales Partner"], function(i, doctype) {
		var name = frm.doc[doctype.toLowerCase().replace(/ /g, "_")];
		if(name && locals[doctype] && locals[doctype][name])
			frappe.model.remove_from_locals(doctype, name);
	});
});

cur_frm.cscript.refresh = function(doc) {
	cur_frm.communication_view = new frappe.views.CommunicationList({
		list: frappe.get_list("Communication", {"parent": doc.name, "parenttype": "Contact"}),
		parent: cur_frm.fields_dict.communication_html.wrapper,
		doc: doc,
		recipients: doc.email_id
	});
}

cur_frm.cscript.hide_dialog = function() {
	if(cur_frm.contact_list)
		cur_frm.contact_list.run();
}
