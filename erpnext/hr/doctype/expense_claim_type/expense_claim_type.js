frappe.ui.form.on("Expense Claim Type", "onload", function(frm, dt, dn){
	frm.fields_dict["default_account"].get_query = function(doc) {
	return {
		filters:{
			"is_group": 0
			}
		}
	}
})