erpnext.updates = [
	["14th December 2012", [
		"Website Module: Major Refactor - removed framework code from website."
	]],
	["12th December 2012", [
		"Attachments: Attachments can be set as URLs or File Uploads. This will help if people want to share documents from Google Docs, Dropbox and other such services (esp for the Product listings on websites).",
		"Global Defaults: Session Expiry can now be set in Global Defaults.",
	]],
	["6th December 2012", [
		"Rename: Cost Center, Item Group, Customer Group, Supplier Type, Territory, Sales Person can now be renamed.",
		"Newsletter: Send newsletter to a list of email addresses.",
	]],
	["5th December 2012", [
		"Leave Application: Now can set approver.",
		"New Roles Added: Leave Approver and Expense Approver.",
		"Production Order: Now linked with Sales Order.",
		"Production Planning Tool: The field 'Allow SA items as raw material' has been renamed to 'Use multi-level BOM', 'Include in plan' column from SO table has been deleted",
		"Batch Numbers: Batch nos are now filtered with Item and available qty at time of selection in transactions.",
		"BOM: 'Update Costing' button has been deleted, once submitted cost are fixed.",
		"[For indian customer only] Deprecated TDS related documents and fields. Old TDS amount added into tax table in Purchase Invoice and entries table in case of JV",
	]],
	["4th December 2012", [
		"POS / Mode of Payment: Select default bank / cash account in Mode of Payment and it will be automatically selected in POS Invoice.",
		"Email: Add contact name as 'Dear so-and-so' in Email.",
		"Report Builder: Remember last column setup for users",
		"Report Builder: Autoset column width (remember)",
	]],
	["3rd December 2012", [
		"Linked With: Added new Linked with in all Forms.",
		"Rename Tool: Documents that can be renamed will have a 'Rename' option in the sidebar (wherever applicable).",
		"Chart of Accounts: Ability to rename / delete from Chart of Accounts.",
		"Delivery and Billing status now updated in sales order, if POS made against that sales order"
	]],
	["30th November 2012", [
		"Auto Notifications: System will prompt user with pre-set message for auto-notification.",
		"Employee: Users with role Employee will only be able to see their Employee Records.",
		"Leave Application: Users with role Employee can now apply for leaves. HR User will be able to set Approval or Rejection.",
	]],
	["29th November 2012", [
		"EMail: Form Emails are now via Communication (with Rich Text Etc.).",
	]],
	["28th November 2012", [
		"Profile: Profile Settings (My Settings...) is now the Profile Form.",
		"Financial Analytics: Show Net Profit/Loss",
	]],
	["27th November 2012", [
		"Communication: Made common communication thread and added it in Lead, Contact.",
	]],
	["26th November 2012", [
		"Email: Added User Signature",
		"Support Ticket: Added link to Lead / Contact. If incoming ticket is not from an existing Lead / Contact, create a new Lead",
	]],
	["24ht November 2012", [
		"Support Ticket: Support Ticket Response is now Communication",
	]],
	["23rd November 2012", [
		"General Ledger: Auto-suggest Accounts for filtering",
		"Calendar: User Interface Fixes, small text for events",
		"Email Settings: Setup outgoing email without a login id \
			(applicable for a local email server)",
		"Delivered Items To Be Billed: New report in 'Accounts'",
	]],
	["22nd November 2012", [
		"Support Ticket: Compose a reply using Markdown",
		"Supplier Link Field: Search by Supplier Name instead of ID",
		"Supplier Link Field: Show only ID in auto-suggest \
			if ID created using Supplier Name (as defined in Global Defaults)",
	]],
	["21st November 2012", [
		"Tree Report: Added missing expand / collapse buttons.",
		"List View: Do not show restricted records, as defined in Permission Manager.",
		"Customer Link Field: Search by Customer Name instead of ID",
		"Customer Link Field: Show only ID in auto-suggest \
			if ID created using Customer Name (as defined in Global Defaults)",
		"Letter Head: Fixed bug causing cursor position to reset in Content",
	]],
	["20th November 2012", [
		"Auto-suggest: Show main label in bold",
		"Data Import Tool: Fixed #Name error faced by MS Excel users in import template",
	]],
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