pscript.onload_contact = function(wrapper) {
	$('#content-contact-us .btn.primary').click(function() {
		var me = this;
		var args = {};
		args.name = $('#content-contact-us [name="contact-name"]').val();
		args.email = $('#content-contact-us [name="contact-email"]').val();
		args.message = $('#content-contact-us [name="contact-message"]').val();
		
		if(!validate_email(args.email)) {
			msgprint('Please enter a valid email id');
			return;
		}
		
		if(args.name && args.email && args.message) {
			$(this).set_working();
			$c_page('website', 'contact', 'send', args, function(r) {
				$('#content-contact-us [name*="contact"]').val('');
				$(me).done_working();
			});
		} else {
			msgprint("Please enter info in all the fields.")
		}
	});
	
	$('#content-contact-us :input').keyup(function(ev) {
		if(ev.which == 13) {
			$('#content-contact-us .btn.primary').click();
		}
	});
}