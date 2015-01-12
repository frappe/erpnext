// Make Journal Entry
frappe.ui.form.on("Fixed Asset Account", "post_journal_entry", function(frm) {

	return  frappe.call({
		method: 'post_journal_entry',
		doc: frm.doc,
		callback: function(r) {
			frm.fields_dict.post_journal_entry.$input.addClass("btn-primary");
			var doclist = frappe.model.sync(r.message);
			frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
});


