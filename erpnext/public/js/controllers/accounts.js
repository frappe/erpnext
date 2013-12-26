
// get tax rate
cur_frm.cscript.account_head = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(!d.charge_type && d.account_head){
		msgprint("Please select Charge Type first");
		wn.model.set_value(cdt, cdn, "account_head", "");
	} else if(d.account_head && d.charge_type!=="Actual") {
		wn.call({
			type:"GET",
			method: "controllers.accounts_controller.get_tax_rate", 
			args: {"account_head":d.account_head},
			callback: function(r) {
			  wn.model.set_value(cdt, cdn, "rate", r.message || 0);
			}
		})
	}
}
