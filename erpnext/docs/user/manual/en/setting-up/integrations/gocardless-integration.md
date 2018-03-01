# Setting up GoCardless

To setup GoCardless, go to `Explore > Integrations > GoCardless Settings`

## Setup GoCardless

To enable GoCardless in your ERPNext account, you need to configure the following parameters and Access Token and optionally (but highly recommended), a Webhooks Secret key.


You can setup several GoCardless payment gateways if needed. The choice of payment gateway account will determine which GoCardless account is used for the payment.

![GoCardless Settings](/docs/assets/img/setup/integrations/gocardless_account.png)

On enabling service, the system will create a Payment Gateway record and an Account head in chart of account with account type as Bank.

![GoCardless COA](/docs/assets/img/setup/integrations/gocardless_coa.png)

It will also create a payment gateway account. You can change the default bank account if needed and create a template for the payment request.

![Payment Gateway Account](/docs/assets/img/setup/integrations/payment_gateway_account_gocardless.png)

After configuring the Payment Gateway Account, your system is able to accept online payments through GoCardless.

## SEPA Payments Flow

When a new payment SEPA payment in initiated, the customer is asked to enter his IBAN (or local account number) and to validate a SEPA mandate.

Upon validation of the mandate, a payment request is sent to GoCardless and processed.

If the customer has already a valid SEPA mandate, when instead of sending a payment request to the customer, the payment request is directly sent to GoCardless without the need for the customer to validate it.
The customer will only receive a confirmation email from GoCardless informing him that a payment has been processed.


## Mandate cancellation

You can setup a Webhook in GoCardless to automatically disabled cancelled or expired mandates in ERPNext.

The Endpoint URL of your webhook should be: https://yoursite.com/api/method/erpnext.erpnext_integrations.doctype.gocardless_settings.webhooks

In this case do not forget to configure your Webhooks Secret Key in your GoCardless account settings in ERPNext.


## Supported transaction currencies
	"EUR", "DKK", "GBP", "SEK"
