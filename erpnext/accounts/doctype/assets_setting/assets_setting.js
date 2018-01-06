// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assets Setting', {
refresh: function(frm) {
		frm.disable_save();
	},
	scrape_date:function(frm) {
		if (frm.doc.scrape_date){
			frappe.call({
	                method: "erpnext.accounts.doctype.assets_setting.assets_setting.get_scrapped_assets",
	                args: {
	                    sc_date: frm.doc.scrape_date,
	                    settings:frm.doc
	                },
	                callback: function(r) {
	                    if (r.message) {
	                        frm.set_value('assets',r.message)
	                    	cur_frm.refresh_fields("assets")
	                    	console.log(r.message)
	                    }
	                    else{
	                    	frm.set_value('assets',r.message)
	                    	cur_frm.refresh_fields("assets")
	                    	frappe.msgprint("There is no assets to depreciation in that date")

	                    }
	                }
	            });
			}
	},
	make_depreciation_entry: function(frm) {
	
		frappe.call({
			doc:frm.doc,
			method: "make_depreciation_entry_bulk",
			callback: function(r) {
				console.log(r.message)
				show_alert('Journal Entry Created '+r.message, 5);
				msgprint("<b>Journal Entry Created</b>"
					+ "<hr>"
					+ "<ul>"
						+ "<li><b>"+r.message+"</b> Memory</li>"
					+ "</ul>")
				frm.set_value('assets',[])
				frm.set_value('last_journal_entry',r.message)
				cur_frm.refresh_fields("assets");
			}
		})
	
}
});


