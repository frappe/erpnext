#Setup Two Factor Authentication

##Enable Two Factor Authentication (2FA)

Activate two factor authentication by running the command.

`bench --site [sitename] enable_two_factor_auth true` 

Specify the following in System Settings

* The method of OTP validation (OTP App = TOTP using Soft or Hard Token while Email/SMS = HOTP using Email or SMS
* The expiry time for the QR Code on the server if OTP App is specified
* The OTP Issuer Name.

<img alt="Enable Two Factor Auth" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-1.png">


On activation of 2FA from setup, it is also activated for the Role "All". In this way, all users including the Administrator have to perform a 2nd level authentication with a token. By unchecking the "Two Factor Authentication" checkbox in the "All" role and enabling it in other roles, the need to login with a token can be limited to specific roles. 2FA does not apply to login by Web Users and API login

<img alt="Role Enable Two Factor Auth" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-2.png">

If using SMS authentication, please make sure that your SMS settings are updated

<img alt="SMS Settings" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-3.png">

If using Email, make sure that your outgoing Email account settings are updated

<img alt="Email Settings" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-4.png">

When the new user tries to log in for the first time in a system that has two-factor authentication enabled and which has the authentication option as OTP App, an email is sent containing a link to the QR Code.

<img alt="Email Notify Two Factor" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-5.png">
<img alt="QR Code Page" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-6.png">

Scanning the QR Code with an authentication app like Google Authenticator registers the access for the user and automatically starts to generate tokens that can be used to login

<img alt="Two Factor Scan App" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor_app.jpeg">

If either of Email/SMS is used as the authentication method, you get notifications also

<img alt="Email and SMS" class="screenshot" src="/docs/assets/img/articles/twofactor/twofactor-8.png">