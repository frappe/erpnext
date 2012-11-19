erpnext.updates = [
	["19th November 2012", [
		"Sales Order: Bugfix - Shipping Address should be a Link field.",
		"Link Fields: Search Profile, Employee and Lead using Full Names instead of ID.",
		"Knowledge Base: Always open links, embedded in an answer, in a new tab."
	]],
	["16th November 2012", [
		"Appraisal: Cleaned up form and logic. Removed complex and unnecessary approval logic, \
			the appraiser can select the template and role and make an appraisal. \
			Normal user can see self created Appraisals. HR Manager can see all Appraisals.",
		"Project: Bugfix in Gantt Chart (caused due to jquery conflict)",
		"Serial No: Ability to rename.",
		"Rename Tool: Added Serial No to rename tool.",
	]],
	["15th November 2012", [
		"Customer Issue: Moved all allocations to 'Assigned' so that there is avoid duplication fo features.",
		"Letter Head: Show preview, make upload button more visible.",
		"Price List: Removed import, now import from Data Import Tool.",
		"Data Import Tool: More help in template.",
	]],
	["14th November 2012", [
		"Employee: If User ID is set, Employee Name will be updated in defaults and will appear automatically in all relevant forms.",
		"Backups: Link to download both database and files.",
	]],
	["13th November 2012", [
		"Customize Form View: Validate correct 'Options' for Link and Table fields.",
		"Report Builder (new): Added formatters for Date, Currency, Links etc.",
		"Trial Balance (new): Feature to export Ledgers or Groups selectively. Indent Groups with spaces.",
		"General Ledger (new): Will show entries with 'Is Opening' as Opening.",
		"General Ledger (new): Show against account entries if filtered by account.",
	]],
	["12th November 2012", [
		"Document Lists: Automatically Refresh lists when opened (again).",	
		"Messages: Popups will not be shown (annoying).",	
		"Email Digest: New option to get ten latest Open Support Tickets.",
		"Journal Voucher: 'Against JV' will now be filtered by the Account selected.",
		"Query Report: Allow user to rename and save reports.",
		"Employee Leave Balance Report: Bugfix"
	]]
]


wn.pages['latest-updates'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Latest Updates',
		single_column: true
	});
		
	var parent = $(wrapper).find(".layout-main");
	
	$("<p class='help'>Report issues by sending a mail to <a href='mailto:support@erpnext.com'>support@erpnext.com</a> or \
		via <a href='https://github.com/webnotes/erpnext/issues'>GitHub Issues</a></p><hr>").appendTo(parent);
	
	
	$.each(erpnext.updates, function(i, day) {
		$("<h4>" + day[0] + "</h4>").appendTo(parent);
		$.each(day[1], function(j, item) {
			$("<p>").html(item).appendTo(parent);
		})
		$("<hr>").appendTo(parent);
	});
}