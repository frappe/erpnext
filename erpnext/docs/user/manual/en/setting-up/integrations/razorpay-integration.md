# Razorpay Integration

#Setting up Razorpay

A payment gateway is an e-commerce application service provider service that authorizes credit card payments for e-businesses, online retailers, bricks and clicks, or traditional brick and mortar.

A payment gateway facilitates the transfer of information between a payment portal (such as a website, mobile phone or interactive voice response service) and the Front End Processor or acquiring bank.

To setup Razorpay,
`Explore > Integrations > Razorpay Settings`

#### Setup  Razorpay 

To enable Razorpay payment service, you need to configure parameters like API Key, API Secret
<img class="screenshot" alt="Razorpay Settings" src="{{docs_base_url}}/assets/img/setup/integrations/razorpay_settings.png">

On enabling service, the system will create Payment Gateway record and Account head in chart of account with account type as Bank.

<img class="screenshot" alt="Razorpay COA" src="{{docs_base_url}}/assets/img/setup/integrations/razorpay_coa.png">

Also it will create Payment Gateway Account entry. Payment Gateway Account is configuration hub from this you can set account head from existing COA, default Payment Request email body template.

<img class="screenshot" alt="Payment Gateway Account" src="{{docs_base_url}}/assets/img/setup/integrations/payment_gateway_account_razorpay.png">

After enabling service and configuring Payment Gateway Account your system is able to accept online payments.

####Supporting transaction currencies
INR
