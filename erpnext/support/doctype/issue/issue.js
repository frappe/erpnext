frappe.ui.form.on("Issue", {
	"onload": function(frm) {
		frm.email_field = "raised_by";
	},

	"refresh": function(frm) {
		if(frm.doc.status==="Open") {
			frm.add_custom_button(__("Close"), function() {
				frm.set_value("status", "Closed");
				frm.save();
			});
		} else {
			frm.add_custom_button(__("Reopen"), function() {
				frm.set_value("status", "Open");
				frm.save();
			});
		}
	},

	timeline_refresh: function(frm) {
		// create button for "Add to Knowledge Base"
		if(frappe.model.can_create('Help Article')) {
			$('<button class="btn btn-xs btn-default btn-add-to-kb pull-right" style="margin-top: -2px">'+
				__('Add to Knowledge Base') + '</button>')
				.appendTo(frm.timeline.wrapper.find('.comment-header'))
				.on('click', function() {
					var content = $(this).parents('.timeline-item:first').find('.timeline-item-content').html();
					var doc = frappe.model.get_new_doc('Help Article');
					doc.title = frm.doc.subject;
					doc.content = content;
					frappe.set_route('Form', 'Help Article', doc.name);
				});
		}
	}
});
