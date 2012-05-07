window._version_number = "d9f42d1e15307de62f68d890d4e40adbe2472a85153ddc965775bebd";
window.home_page = "Login Page";
// footer signup widget
// automatically adds it to the .layout-main div of the page
// adds events and also random goodies.

erpnext.set_request_signup = function(page_name) {
  
  // goodies
  var goodies = [
     "ERPNext also contains a module to build your website. \
The way it works is, when you log out, the app becomes your website. \
This website is generated from ERPNext.",

     "You can add custom fields to your transactions in ERPNext to capture specific information about your business.",

     "All forms in ERPNext can be customized, if you feel there are features you do not want to use, you can hide them.",

     "You can email transactions like Quotations and Invoices directly from the system. You can also set this process to become automatic",

     "You can create your own Roles and assign user to those roles. You can also set detailed permissions for each role in transactions.",

     "ERPNext allows you to assign any transaction like an Invoice or Customer Issue to a user. You can also add comments on any transaction."

  ];


  // add the footer

  $('#page-' + page_name + ' .layout-main').append('<div class="page-footer">\
<h2 style="padding: 0px">Try before you buy. \
Request a 30-day Free Trial.</h2><br>\
\
<input name="company_name" type="text" placeholder="Company Name"> \
<input name="sender_name" type="text" placeholder="Your Name"> \
<input name="email" type="text" placeholder="Email"> \
<input name="password" type="password" placeholder="Password"> \
<button class="btn btn-success btn-small btn-request">Request</button>\
\
<p>Note: Free trials usually take one business day to setup. \
Please fill out your genuine information because we verify \
your name and company before setting up a demo to \
ensure that spammers don\'t crash our servers. \
If you would like to see something right now, \
<a href="#!demo">jump to the demo.</a></p>\
\
<p style="font-size: 90%; margin-top: 10px;">\
<i class="icon-hand-right"></i> <b>ERPNext Goodies:</b> <span class="goodie">'

+ goodies[parseInt(Math.random() * goodies.length)]+

'</goodie></p>\
</span>');

  // bind the events

  $('#page-'+page_name+' .btn-request').click(function() {

    var page = $('#page-' + wn.container.page.page_name);
    var args = {
        sender_name: page.find('[name="sender_name"]').val(),
        company_name: page.find('[name="company_name"]').val(),
        email: page.find('[name="email"]').val(),
        password: page.find('[name="password"]').val()
      }

    if(!(args.sender_name && args.company_name && args.email && args.password)) {
       msgprint("All fields are necessary. Please try again.");
       return;
    }


    erpnext.send_message({
      subject:'New Trial Request',
      sender: page.find('[name="sender_name"]').val(),
      message: args,
      callback: function() {
        page.find(':input').val('');
      }
    });
  });
}