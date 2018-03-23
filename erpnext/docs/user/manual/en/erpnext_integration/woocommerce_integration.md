
# WooCommerce Integration 

#### Setting Up WooCommerce on ERPNEXT:-

Steps:- 

1. From Awesome-bar, go to "Woocommerce Settings" doctype.

2. From your woocommerce site, generate "API consumer key" and  "API consumer secret" using Keys/Apps tab.

3. Paste those generated "API consumer key" and  "API consumer secret" into "Woocommerce Settings" doctype.

4. In "Woocommerce Server URL" paste the url of your site where ERPNEXT is installed.

5. Make sure "Enable Sync" is checked.

6. Select Account type from Account Details Section.

7. Click Save.

8. After saving, "Secret" and "Endpoint" are generated automatically and can be seen on "Woocommerce Settings" doctype.

9. Now from your woocommerce site, click on webhooks option and click on "Add Webhook".

10. Give name to the webhook of your choice. Click on Status dropdown and select "Active". Select Topic as "Order Created". Copy the "Endpoint" from "Woocommerce Settings" doctype and paste it in "Delivery URL" field. Copy "Secret" from "Woocommerce Settings" doctype and paste it in "Secret" field. Keep API VERSION as it is and click on Save Webhook.

11. Now the WooCommerce is successful setup on your system.

<img class="screenshot" alt="Woocommerce Integration" src="{{docs_base_url}}/assets/img/erpnext_integrations/woocommerce_setting_config.gif">


### Note:-  In above gif, inplace of delivery url on woocommerce website, you need to paste the url you will obtain after saving the "Woocommerce Settings" page (i.e. Endpoint from "Woocommerce Settings"). I pasted other url because I was using localhost. Please paste your endpoint in place of Delivery URL.
	


#### WooCommerce Integration Working:- 

Steps:- 

1. From your Woocommerce website, register yourself as a user.

2. Now Click on Address Details and provide the required details.

3. For start shopping, click on Shop option and now available products can be seen.

4. Add the desired products into cart and click on View Cart.

5. From Cart, once you have added the desired products, you can click on proceed to checkout.

6. All billing details and Order details can be seen now. Once you are ok with it, click on Place Order button.

7. "Order Received" message can been seen indicating that the order is placed successfully.

8. Now on system where ERPNEXT is installed check the following doctypes: Customer, Address, Item, Sales Order.

<img class="screenshot" alt="Woocommerce Integration" src="{{docs_base_url}}/assets/img/erpnext_integrations/woocommerce_demo.gif">