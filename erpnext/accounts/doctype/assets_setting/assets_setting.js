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
	l=frm.doc.assets
	for (asset in l )
	{
	if (!l[asset]['journal_entry']) {
		console.log(l[asset]['asset_name'])
		frappe.call({
			method: "erpnext.accounts.doctype.asset.depreciation.make_depreciation_entry",
			args: {
				"asset_name": l[asset]['asset_name'],
				"date": frm.doc.scrape_date
			},
			callback: function(r) {

				frm.set_value('assets',[])
	                    	
				cur_frm.refresh_fields("assets");
			}
		})
	}
}

	
}
});


