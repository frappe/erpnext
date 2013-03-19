
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
	} else if(window.is_forgot) {
		args.cmd = "reset_password";
		args.user = $("#login_id").val();
		
		if(!args.user) {
			login.set_message("Valid Login Id required.");
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
			$("input").val("");
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
	$("#password-row, #sign-up-wrapper, #login_message").toggle(false);
	$("#full-name-row").toggle(true);
	$("#login_btn").html("Register");
	$("#forgot-wrapper").html("<a onclick='location.reload()' href='#'>Login</a>")
	window.is_sign_up = true;
}

login.show_forgot_password = function() {
	$("#login_wrapper h3").html("Forgot");
	$("#login-label").html("Email Id");
	$("#password-row, #sign-up-wrapper, #login_message").toggle(false);
	$("#login_btn").html("Send Password");
	$("#forgot-wrapper").html("<a onclick='location.reload()' href='#'>Login</a>")
	window.is_forgot = true;
}

login.set_message = function(message, color) {
    $('#login_message').html(message).toggle(true);	
}