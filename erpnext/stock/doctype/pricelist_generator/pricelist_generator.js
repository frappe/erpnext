// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PriceList Generator', {
	item_group: function(frm) {
		frm.call({
            method:"get_items_brand",
            doc:frm.doc,
            callback: function(r) {
                if(r.message){
                        console.log("***",r.message);
                    }
                }
        });
	}

});
