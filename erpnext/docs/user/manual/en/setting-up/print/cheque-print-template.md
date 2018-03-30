#Cheque Print Template

Business involves making payment to various parties like suppliers and employees. Payment can be made in various modes like cash, NEFT or cheque. If you are making a payment via cheque, you can also create a Print Format for printing Cheque from ERPNext based on the Payment Entry.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/sample-cheque.jpg">

Using the Cheque Print Template you can generate a new Print Format based. It will be created based the cheque format provided by your bank. 

####Create New

To create a new Print Format based on the specific cheque’s format, go to:

`Account > Tools > Cheque Printing Template > New`

In the Cheque Print Template, for each value (say Payee, Date), exact co-ordinates are provided based on where that value should be printed on a cheque. Co-ordinates are provided in centi-meter.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/cheque-1.png">

####New Format via Scanning

To speed up creation of a new cheque printing format, you can upload scanned image of the cheque. Considering the scanned image for the cheque, system automatically updates co-ordinates for each value like party name, amount, date, amount in words etc.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/cheque-2.png">

####New format by manual entry
You can manually provide the co-ordinate for each value based on where you want to to be printed on the cheque.

####Preview
Based on co-ordinates provided for all the values, a preview be shown as to how the values will be printed on the cheque.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/cheque-3.png">

####New Print Format

If the preview looks promising, click on the button to create a new Print Format for printing cheque. Based on the values provided in the Cheque Print Template, the system will auto-generate an HTML script for the cheque’s Print Format.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/cheque-4.png">

####Printing Cheque

New print format generated for the cheque will be visible in the Payment Entry form. After creating the payment entry, you will be able to print transaction details on the cheque.

<img class="screenshot" alt="Sample Cheque" src="{{docs_base_url}}/assets/img/setup/print/cheque-5.gif">


