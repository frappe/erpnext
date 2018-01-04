# Email Inbox

Business involves many transactional emails exchanges with parties like Customers and Suppliers, and within a company. Email Inbox feature allows you pull all your business emails into your ERPNext account. Accessing all the business emails with other transactions details makes ERPNext a single platform for accessing complete business information in one place.

In ERPNext, you can configure Email Inbox for each System User. Following are the detailed steps to configure Email Inbox for a User.

#### Step 1: Create User

As mentioned above, you can configure Email Inbox for a System User only. Hence ensure that you have added yourself and your colleagues as a User and assigned them required permissions.

To add new User, go to:

`Setup > User > New User`

<img class="screenshot" alt="Email User" src="/docs/assets/img/setup/email/email-user.png">

#### Step 2: Create Email Domain

To be able to send and receive emails into your ERPNext from other email service (like WebMail or Gmail), you should setup an Email Domain master. In this master, email gateway details like SMTP Address, Port No., IMAP/POP3 address details are captured. If you have ever configured a local email client (like Outlook), Email Domain master requires details to be fed in the similar way.

To add new Email Domain, go to:

`Setup > Emails > Email Domain > New`

<img class="screenshot" alt="Email Domain" src="/docs/assets/img/setup/email/email-domain.png">

Once you have configured an Email Domain for your Email Service, it will be used for creating Email Accounts for all the Users in your ERPNext account.

<div class=well>If you use one of the following Email Service, then you need not create Email Domain in your ERPNext account. In ERPNext, Email Domain for the following Services is available out-of-the-box and you can directly proceed to creating Email Account.
<ul>
<li>Gmail</li>
<li>Yahoo</li>
<li>Sparkpost</li>
<li>SendGrid</li>
<li>Outlook.com</li>
<li>Yandex.mail</li>
<ul>
</div>

#### Step 3: Email Account

Create an Email Account based on the Email ID of the User. For each User who's email account is to be integrated with ERPNext, an Email Account master should be created for it. 

If you are creating an Email Account for your colleague who's Email Password is unknown to you, then check field "Awaiting Password". As per this setting, a User (for whom Email Account is created) will get a prompt to enter email password when accessing his/her ERPNext Account.

<img class="screenshot" alt="Email Password" src="/docs/assets/img/setup/email/email-password.png">

In the Email Account, select Email Domain only if you are using Email Service other than Email Services listed above. Else, you can just select Email Service, leave Email Domain blank and proceed forward.

<img class="screenshot" alt="Email Service" src="/docs/assets/img/setup/email/email-service.png">

>If you are creating an Email Account for Email Inbox of a User, then leave Append To field as blank.

For more details on how to setup Email Account, [click here](/docs/user/manual/en/setting-up/email/email-account.html").

#### Step 4: Linking Email Account in User master

Once an Email Account is created for an User, select that Email Account in the User. This will ensure that emails pulled from the said Email ID will accessible only to this User in your ERPNext account.

<img class="screenshot" alt="Email User Link" src="/docs/assets/img/setup/email/email-user-link.png">

## Email Inbox

If you have correctly configured Email Inbox as instructed above, then on the login of a User, Email Inbox icon will be visible. This will navigate user to Email Inbox view within the ERPNext account. All the Emails received on that email will be fetch and listed in the Email Inbox view. User will be able to open emails and take various actions against it.

<img class="screenshot" alt="Email Inbox" src="/docs/assets/img/setup/email/email-inbox.png">

#### Folders

In ERPNext, you can link multiple Email Accounts with the single User. To switch to Inbox of different email account and access other folders like Sent Emails, Spam, Trash, check Email Inbox option in the left bar.

<img class="screenshot" alt="Email Folders" src="/docs/assets/img/setup/email/email-folders.png">

#### Actions

On the emails in your inbox, you can take various actions like Reply, Forward, Mark as Spam or Trash.

<img class="screenshot" alt="Email Actions" src="/docs/assets/img/setup/email/email-actions.png">

#### Make Options

The Email Inbox within ERPNext also allow you to quickly create ERPNext transaction based on email received. From an Email itself, you can a Issue, Lead or Opportunity based on the context of the email.

<img class="screenshot" alt="Make from Email" src="/docs/assets/img/setup/email/make-from-email.png">


