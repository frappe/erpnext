# Eine benutzerdefinierte Schaltfläche hinzufügen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

	frappe.ui.form.on("Event", "refresh", function(frm) {
		frm.add_custom_button(__("Do Something"), function() {
			// When this button is clicked, do this
			
			var subject = frm.doc.subject;
			var event_type = frm.doc.event_type;
			
			// do something with these values, like an ajax request 
			// or call a server side frappe function using frappe.call
			$.ajax({
				url: "http://example.com/just-do-it",
				data: {
					"subject": subject,
					"event_type": event_type
				}
				
				// read more about $.ajax syntax at http://api.jquery.com/jquery.ajax/
			
			});
		});
	});

{next}
