// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

$(document).ready(function() { 

	$('.btn-send').click(function() {
		var email = $('[name="email"]').val();
		var message = $('[name="message"]').val();

		if(!(email && message)) {
			msgprint("Please enter both your email and message so that we \
				can get back to you. Thanks!");
			return false;
		}

		if(!valid_email(email)) {
				msgprint("You seem to have written your name instead of your email. \
					Please enter a valid email address so that we can get back.");
				$('[name="email"]').focus();
				return false;
		}

		$("#contact-alert").toggle(false);
		erpnext.send_message({
			subject: $('[name="subject"]').val(),
			sender: email,
			message: message,
			callback: function(r) {
				msgprint(r.message);
				$(':input').val('');
			}
		});
	return false;
	});

});

var msgprint = function(txt) {
	if(txt) $("#contact-alert").html(txt).toggle(true);
}
