# E-Mail-Konto
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Sie können in ERPNext viele verschiedene E-Mail-Konten für eingehende und ausgehende E-Mails verwalten. Es muss mindestens ein Standard-Konto für ausgehende E-Mails und eines für eingehende E-Mails geben. Wenn Sie sich in der ERPNext-Cloud befinden, dann werden die Einstellungen für ausgehende E-Mails von uns getroffen.

**Anmerkung, wenn Sie das System selbst einrichten:** Für ausgehende E-Mails sollten Sie Ihren eigenen SMTP-Server einrichten oder sich bei einem SMTP Relay Service wie mandrill.com oder sendgrid.com, der den Versand einer größeren Menge von Transaktions-E-Mails erlaubt, registrieren. Standard-E-Mail-Services wie GMail beschränken Sie auf eine Höchstgrenze an E-Mails pro Tag.

### Standard-E-Mail-Konten

ERPNext erstellt standardmäßig Vorlagen für einige E-Mail-Konten. Nicht alle sind aktiviert. Um sie zu aktivieren, müssen Sie Ihre Konteneinstellungen bearbeiten.

Es gibt zwei Arten von E-Mail-Konten, ausgehend und eingehend. E-Mail-Konten für ausgehende E-Mails verwenden einen SMTP-Service, eingehende E-Mails verwenden einen POP-Service. Die meisten E-Mail-Anbieter wie GMail, Outlook oder Yahoo bieten diese Seriveleistungen an.

<img class="screenshot" alt="Kriterien definieren" src="{{docs_base_url}}/assets/img/setup/email/email-account-list.png">

### Konten zu ausgehenden E-Mails

Alle E-Mails, die vom System aus versendet werden, sei es von einem Benutzer zu einem Kontakt oder als Transaktion oder als Benachrichtung, werden aus einem Konto für ausgehende E-Mails heraus versendet.

Um ein Konto für ausgehende E-Mails einzurichten, markieren Sie die Option **Ausgehend aktivieren** und geben Sie die Einstellungen zum SMTP-Server an. Wenn Sie einen bekannten E-Mail-Service nutzen, wird das vom System für Sie voreingestellt.

<img class="screenshot" alt="Ausgehende E-Mails" src="{{docs_base_url}}/assets/img/setup/email/email-account-sending.png">

### Konten zu eingehenden E-Mails

Um ein Konto für eingehende E-Mails einzurichten, markieren Sie die Option **Eingehend aktivieren** und geben Sie die Einstellungen zum POP3-Server an. Wenn Sie einen bekannten E-Mail-Service nutzen, wird das vom System für Sie voreingestellt.

<img class="screenshot" alt="Eingehende E-Mails" src="{{docs_base_url}}/assets/img/setup/email/email-account-incoming.png">

### Wie ERPNext Antworten handhabt

Wenn Sie aus ERPNext heraus eine E-Mail an einen Kontakt wie z. B. einen Kunden versenden, dann ist der Absender gleich dem Benutzer, der die E-Mail versendet. In den Einstellungen zu **Antworten an** steht die E-Mail-ID des Standardkontos für den Posteingang (z. B. replies@yourcompany.com). ERPNext entnimmt diese E-Mails automatisch aus dem Posteingang und hängt Sie an die betreffende Kommunikation an.

### Benachrichtigung über unbeantwortete Nachrichten

Wenn Sie möchten, dass ERPNext Sie benachrichtigt, wenn eine E-Mail für eine bestimmte Zeit unbeantwortet bleibt, dann können Sie die Option **Benachrichtigen, wenn unbeantwortet** markieren. Hier können Sie die Anzahl der Minuten einstellen, die das System warten soll, bevor eine Benachrichtigung gesendet wird, und den Empfänger.

<img class="screenshot" alt="Eingehende Email" src="{{docs_base_url}}/assets/img/setup/email/email-account-unreplied.png">

{next}
