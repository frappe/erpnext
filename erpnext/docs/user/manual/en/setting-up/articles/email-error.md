# Email Error in Sending or Receiving

In ERPNext, you can customize the Incoming and Outgoing Email Gateway. On saving an Email Account, ERPNext tries establishing a connection with your email gateway. If your ERPNext account is able to connect fine, then Email Account is saved successfully. If not, then you might receive an error as below.  

<img class="screenshot" alt="Email Error" src="/docs/assets/img/articles/email-error.png">

This indicates that using login credentials and other email gateway details provided in the Email Account, ERPNext is not able to connect to your email server. Please ensure that you have entered valid email credentials for your Email Gateway. Once you have configured Email Account successfully, you should be able to send and receive emails from your ERPNext account fine.

Note: Your ERPNext account is connected with an ERPNext email server by default. If you don't want to use your own email server, you can continue sending emails using ERPNext email server, without any configuration required in the Email Account.