window.home_page = "home";
// footer signup widget
// automatically adds it to the .layout-main div of the page
// adds events and also random goodies.

erpnext.set_request_signup = function(page_name) {
  
  // goodies
  var goodies = [
     "ERPNext also contains a module to build your website. \
    The way it works is, when you log out, the app becomes your website. \
    This website is generated from ERPNext.",

     "You can add custom fields to your transactions in ERPNext to \
     capture specific information about your business.",

     "All forms in ERPNext can be customized, if you feel there are \
     features you do not want to use, you can hide them.",

     "You can email transactions like Quotations and Invoices directly \
     from the system. You can also set this process to become automatic",

     "You can create your own Roles and assign user to those roles. \
     You can also set detailed permissions for each role in transactions.",

     "ERPNext allows you to assign any transaction like an Invoice \
     or Customer Issue to a user. You can also add comments on any \
     transaction.",
     
     "Stay on top with a daily, weekly or montly email summarizing all your business\
     activites and accounting data like Income, Receivables, Paybles etc.",
     
     "Integrate incoming Support queries to your email into ERPNext. \
     Keep track of open tickets and allocate tickets to your users."

  ];


  // add the footer

  $('#page-' + page_name + ' .layout-main').append('<div class="page-footer">\
<h2 style="padding: 0px">Try before you buy. \
Request a 30-day Free Trial.</h2>\
<ul>\
<li><a href="erpnext-pricing.html">Starts at an un-believable $299 per year.</a>\
<li><a href="http://demo.erpnext.com" target="_blank">\
Show me a full demo (new page).</a>\
<li><a href="sign-up.html">Take me to the sign-up page.</a>\
</ul>\
<p>\
<i class="icon-hand-right"></i> <b>ERPNext Goodies:</b> <span class="goodie">'

+ goodies[parseInt(Math.random() * goodies.length)]+

'</goodie></p>\
<p>ERPNext is <a href="open-source.html">Open Source</a> under the GNU/General Public License.</p>\
<p><g:plusone size="medium" annotation="inline"></g:plusone></p>\
\
<table><tr><td style="width: 115px">\
    <a href="https://twitter.com/erpnext" class="twitter-follow-button" \
    data-show-count="false">Follow @erpnext</a></td>\
    <td style="width: 150px; font-size: 80%; vertical-align: middle;">\
    Get status updates on Twitter.</td></tr>\
</table>');

  // render plusone
  window.gapi && window.gapi.plusone.go();
  
  // render twitter button
  twttr.widgets.load();
}

//////////////// Hide Login for frappe!

$(document).ready(function() {
  setTimeout("$('#login-topbar-item').toggle(false);", 1000);
});

//////////////// Analytics

window._gaq = window._gaq || [];
window._gaq.push(['_setAccount', 'UA-8911157-1']);
window._gaq.push(['_trackPageview']);

(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();


/////////////// Page view

$(window).bind('hashchange', function() {
  window._gaq.push(['_trackPageview', wn.get_route_str()]);
});

/////////////// Update conversion

erpnext.update_conversion = function() {
  $('body').append('<div style="display:inline;">\
<img height="1" width="1" style="border-style:none;" alt="" \
src="http://www.googleadservices.com/pagead/conversion/1032834481/?label=JvAUCLX41gEQsZu_7AM&amp;guid=ON&amp;script=0"/>\
</div>')
};

////////////// Plus One

(function() {
  var po = document.createElement('script'); po.type = 'text/javascript'; po.async = true;
  po.src = 'https://apis.google.com/js/plusone.js';
  var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(po, s);
})();

////////////// Twitter

(function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];
if(!d.getElementById(id)){js=d.createElement(s);js.id=id;
js.src="//platform.twitter.com/widgets.js";
fjs.parentNode.insertBefore(js,fjs);}})(document,"script","twitter-wjs");

