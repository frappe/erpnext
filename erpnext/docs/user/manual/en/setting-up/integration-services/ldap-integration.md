#Setting up LDAP

Lightweight Directory Access Protocol is a centralised access controll system used by many small medium scale organisations.

By settings up LDAP service, you able to login to ERPNext account by using LDAP credentials.

####Step 1: Create Razorpay service

`Explore > Setup > Integration Service`

Make a new Integration Service and select `LDAP` as a service from dropdown then save the document.
After saving a document, click on `LDAP Settings` button, to setup service.

####Step 2: Setup  ldap service

To enable ldap service, you need to configure parameters like LDAP Server Url, Organizational Unit, Base Distinguished Name (DN) and Password for Base DN

<img class="screenshot" alt="LDAP Settings" src="{{docs_base_url}}/assets/img/setup/integration-service/ldap_settings.png">

####Step 3: Enable Service
After setting up credentials on LDAP Settings, go back to LDAP Service record and enable it.
While enabling, it will validate LDAP details and on successful validation, it will enables LDAP login option.

<img class="screenshot" alt="LOGIN via LDAP" src="{{docs_base_url}}/assets/img/setup/integration-service/login_via_ldap.png">