#Setting up PayPal

A payment gateway is an e-commerce application service provider service that authorizes credit card payments for e-businesses, online retailers, bricks and clicks, or traditional brick and mortar.

A payment gateway facilitates the transfer of information between a payment portal (such as a website, mobile phone or interactive voice response service) and the Front End Processor or acquiring bank.

####Step 1: Create PayPal service

`Explore > Setup > Integration Service`

Make a new Integration Service and select `PayPal` as a service from dropdown then save the document.
After saving a document, click on `PayPal Settings` button, to setup service.

####Step 2: Setup  payment service

To enable PayPal payment service, you need to configure parameters like API Username, API Password and Signature.

<img class="screenshot" alt="PayPal Settings" src="{{docs_base_url}}/assets/img/setup/integration-service/paypal_settings.png">

You also can set test payment environment, by settings `Use Sandbox`

####Step 3: Enable Service
After setting up credentials on PayPal Settings, go back to PayPal Service record and enable it.
On enabling service, the system will create Payment Gateway record and Account head in chart of account with account type as Bank.

<img class="screenshot" alt="PayPal COA" src="{{docs_base_url}}/assets/img/setup/integration-service/paypal_coa.png">

Also it will create Payment Gateway Account entry. Payment Gateway Account is configuration hub from this you can set account head from existing COA, default Payment Request email body template.

<img class="screenshot" alt="Payment Gateway Account" src="{{docs_base_url}}/assets/img/setup/integration-service/payment_gateway_account_paypal.png">

After enabling service and configuring Payment Gateway Account your system is able to accept online payments.

####Supporting transaction currencies
AUD, BRL, CAD, CZK, DKK, EUR, HKD, HUF, ILS, JPY, MYR, MXN, TWD, NZD, NOK, PHP, PLN, GBP, RUB, SGD, SEK, CHF, THB, TRY, USD

##Get PayPal credentials

#### Paypal Sanbox API Signature
 - Login to paypal developer account, <a href="https://developer.paypal.com/">PayPal Developer Account</a>
 - From **Accounts** tab. create a new business account.
<img class="screenshot" alt="Payment Request" src="{{ docs_base_url }}/assets/img/setup/integration-service/setup-sanbox-1.png">
 
 - From this account profile you will get your sandbox api credentials
<img class="screenshot" alt="Payment Request" src="{{ docs_base_url }}/assets/img/setup/integration-service/sanbox-credentials.png">


---

#### PayPal Account API Signature
 - Login to PayPal Account and go to profile
<img class="screenshot" alt="Payment Request" src="{{ docs_base_url }}/assets/img/setup/integration-service/api-step-1.png">

 - From **My Selling Tools** go to **api Access**
<img class="screenshot" alt="Payment Request" src="{{ docs_base_url }}/assets/img/setup/integration-service/api-step-2.png">

 - On API Access Page, choose option 2 to generate API credentials
<img class="screenshot" alt="Payment Request" src="{{ docs_base_url }}/assets/img/setup/integration-service/api-step-3.png">
