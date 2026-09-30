frappe.provide("erpnext.utils");

// Warns before creating a follow-up document (e.g. Delivery Note from Sales Order)
// when a draft of the target DocType already exists for the same source document.

erpnext.utils.confirm_if_drafts_exist = async function (source_doc, target_doctype) {
	// resolves true to proceed; fails open so a broken check never blocks creation
	if (!source_doc || !source_doc.name || source_doc.__islocal) {
		return true;
	}

	let drafts;
	try {
		drafts = await frappe.xcall("erpnext.controllers.draft_links.get_existing_drafts", {
			source_doctype: source_doc.doctype,
			source_name: source_doc.name,
			target_doctype: target_doctype,
		});
	} catch (e) {
		console.error(e);
		return true;
	}

	if (!drafts.length) {
		return true;
	}

	return new Promise((resolve) => {
		frappe.confirm(
			get_draft_warning(source_doc, target_doctype, drafts),
			() => resolve(true),
			() => resolve(false)
		);
	});
};

if (frappe.model.add_mapped_doc_guard) {
	frappe.model.add_mapped_doc_guard((mapped_doc, opts) =>
		erpnext.utils.confirm_if_drafts_exist(opts.frm && opts.frm.doc, mapped_doc.doctype)
	);
}

function get_draft_warning(source_doc, target_doctype, drafts) {
	const links = drafts.map((name) => frappe.utils.get_form_link(target_doctype, name, true)).join(", ");

	if (drafts.length === 1) {
		return __("A draft {0} already exists for this {1}: {2}. Do you still want to create a new one?", [
			__(target_doctype),
			__(source_doc.doctype),
			links,
		]);
	}
	return __(
		"{0} draft {1} documents already exist for this {2}: {3}. Do you still want to create a new one?",
		[drafts.length, __(target_doctype), __(source_doc.doctype), links]
	);
}
