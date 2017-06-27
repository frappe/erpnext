# Statutory Requirements for India

As of 2017, India will fall under the new GST (Goods and Services Tax) regime and ERPNext makes it easy for users to track the details of its Supplier and Customers across Invoices and make the required reports.

## GST Features in ERPNext

### 1. Setting up GSTIN

GST Law requires that you maintain the GSTIN number for all your suppliers and vendors. In ERPNext, GSTIN is linked to the **Address**

<img class="screenshot" alt="GST in Customer" src="{{docs_base_url}}/assets/img/regional/india/gstin-customer.gif">

**GST for your Company Address**

You also need to set the Address for your own Company and your Company's GST Number

Go to the Company master and add the GSTIN to your default address.

<img class="screenshot" alt="GST in Company" src="{{docs_base_url}}/assets/img/regional/india/gstin-company.gif">

### 2. Setting up HSN Codes

According to the GST Law, your itemised invoices must contain the HSN Code related to that Item. ERPNext comes pre-installed with all 12,000+ HSN Codes so that you can easily select the relevant HSN Code in your Item

<img class="screenshot" alt="HSN in Item" src="{{docs_base_url}}/assets/img/regional/india/hsn-item.gif">

### 3. Making Tax Masters

To setup Billing in GST, you need to create 3 Tax Accounts for the various GST reporting heads CGST - Central GST, SGST - State GST, IGST - Inter-state GST

Go to your **Chart of Accounts**, under the Duties and Taxes head of your account, create 3 Accounts

**Note:** Usually the rate in CGST and SGST is half of IGST. For example if most of your items are billed at 18%, then create IGST at 18%, CGST and SGST at 9% each.

<img class="screenshot" alt="GST in Customer" src="{{docs_base_url}}/assets/img/regional/india/gst-in-coa.png">

### 4. Make Tax Templates

You will have have to make two tax templates for both your sales and purchase, one for in state sales and other for out of state sales.

In your **In State GST** template, select 2 accounts, SGST and CGST

<img class="screenshot" alt="GST in Customer" src="{{docs_base_url}}/assets/img/regional/india/gst-template-in-state.png">

In your **Out of State GST** template, select IGST

### 5. Making GST Ready Invoices

If you have setup the GSTIN of your Customers and Suppliers, and your tax template, you are ready to go for making GST Ready Invoices!

For **Sales Invoice**,

1. Select the correct Customer and Item and the address where the transaction will happen.
2. Check if the GSTIN of your Company and Supplier have been correctly set.
3. Check if the HSN Number has been set in the Item
4. Select the the **In State GST** or **Out of State GST** template that you have created based on the type of transaction
5. Save and Submit the Invoice

<img class="screenshot" alt="GST Invoice" src="{{docs_base_url}}/assets/img/regional/india/gst-invoice.gif">

### Reports

ERPNext comes with most of your reports you need to prepare your GST Returns. Go to Accounts > GST India head for the list.

<img class="screenshot" alt="GST Menus" src="{{docs_base_url}}/assets/img/regional/india/gst-menu.png">

You can check the impact of your invoice in the **GST Sales Register** and **GST Itemised Sales Register**

<img class="screenshot" alt="GST Itemised Sales Register" src="{{docs_base_url}}/assets/img/regional/india/gst-itemised.png">


