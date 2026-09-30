frappe.provide("erpnext.utils");

/**
 * Business modules that are not ticked on a company.
 * @param {string} company - Company name.
 * @returns {string[]} e.g. ["Stock", "POS"]
 */
erpnext.utils.get_unticked_business_modules = function (company) {
	const company_doc = frappe.get_doc(":Company", company);
	if (!company_doc) return [];

	return (frappe.boot.business_modules || [])
		.filter((m) => m.fieldname in company_doc && !cint(company_doc[m.fieldname]))
		.map((m) => m.module);
};

/**
 * Hide the fields of business modules that a company does not use.
 * Call it in `refresh` and when the company changes.
 * @param {object} frm
 * @param {string} company - Company name. If empty, nothing is hidden.
 * @example erpnext.utils.hide_business_module_fields(frm, frm.doc.company);
 */
erpnext.utils.hide_business_module_fields = function (frm, company) {
	const modules = company ? erpnext.utils.get_unticked_business_modules(company) : [];
	frm.hide_module_fields(modules);
};
