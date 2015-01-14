// Make Journal Entry
frappe.ui.form.on("Fixed Asset Year Close", "post_journal_entry", function(frm) {

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
cur_frm.cscript.company = function (doc,dt,dn) {
	if (doc.company) {
		return frappe.call({
			method: "erpnext.accounts.doctype.fixed_asset_account.fixed_asset_account.validate_default_accounts",
			args: {company: doc.company},
			callback: function(r) {
			}			
		});
	}
}
