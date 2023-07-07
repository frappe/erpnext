$(document).on("toolbar_setup", function() {
	if (erpnext.is_demo_company_setup) {
        console.log("setup");
    }
});

erpnext.is_demo_company_setup = function() {
    frappe.db.get_value("Global Default", "Global Default", "demo_company", function(r) {
        console.log(r);
    });
};