
var login = {};

$(document).ready(function(wrapper) {
	$('#login_btn').click(login.do_login)
		
	$('#password').keypress(function(ev){
		if(ev.which==13 && $('#password').val()) {
			$('form').submit(function() {
				login.do_login();
				return false;
			});
		}
	});
	$(document).trigger('login_rendered');
})

// Login
login.do_login = function(){

    var args = {};
	if(window.is_sign_up) {
		args.cmd = "core.doctype.profile.profile.sign_up";
		args.email = $("#login_id").val();
	    args.full_name = $("#full_name").val();

		if(!args.email || !valid_email(args.email) || !args.full_name) {
			login.set_message("Valid email and name required.");
			return false;
		}

	} else {
		args.cmd = "login"
	    args.usr = $("#login_id").val();
	    args.pwd = $("#password").val();

		if(!args.usr || !args.pwd) {
			login.set_message("Both login and password required.");
			return false;
		}	
	}

	$('#login_btn').attr("disabled", "disabled");
	$("#login-spinner").toggle(true);
	$('#login_message').toggle(false);
	
	$.ajax({
		type: "POST",
		url: "server.py",
		data: args,
		dataType: "json",
		success: function(data) {
			$("#login-spinner").toggle(false);
			$('#login_btn').attr("disabled", false);
			if(data.message=="Logged In") {
				window.location.href = "app.html";
			} else if(data.message=="No App") {
				window.location.href = "index";
			} else {
				login.set_message(data.message);
			}
		}
	})
	
	return false;
}

login.sign_up = function() {
	$("#login_wrapper h3").html("Sign Up");
	$("#login-label").html("Email Id");
	$("#password-label").html("Full Name");
	$("#password-row, #forgot-wrapper, #sign-up-wrapper, #login_message").toggle(false);
	$("#full-name-row").toggle(true);
	$("#login_btn").html("Register");
	window.is_sign_up = true;
}

login.show_forgot_password = function(){
    // create dialog
	var login_id = $("#login_id").val();
	if(!login_id || !valid_email(login_id)) {
		login.set_message("Please set your login id (which is your email where the password will be sent);");
		return;
	}
	login.set_message("Sending email with new password...");
	$("#forgot-password").remove();

	$.ajax({
		method: "POST",
		url: "server.py",
		data: {
			cmd: "reset_password",
			user: login_id,
			_type: "POST"
		},
		success: function(data) {
			login.set_message("A new password has been sent to your email id.", "GREEN");
		}
	})
}

login.set_message = function(message, color) {
    $('#login_message').html(message).toggle(true);	
}