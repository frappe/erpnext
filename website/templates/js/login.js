
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
    args['usr']=$("#login_id").val();
    args['pwd']=$("#password").val();

	if(!args.usr || !args.pwd) {
		login.set_message("Both login and password required.");
	}

	$('#login_btn').attr("disabled", "disabled");
	$('#login_message').toggle(false);
	
	$.ajax({
		type: "POST",
		url: "server.py",
		data: {cmd:"login", usr:args.usr, pwd: args.pwd},
		dataType: "json",
		success: function(data) {
			$('#login_btn').attr("disabled", false);
			if(data.message=="Logged In") {
				window.location.href = "app.html";
			} else {
				login.set_message(data.message);
			}
		}
	})
	
	return false;
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