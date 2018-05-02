# SMS-Einstellungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Um SMS-Dienste in ERPNext zu integrieren, wenden Sie sich an einen Anbieter eines SMS-Gateways der Ihnen eine HTTP-Schnittstelle (API) zur Verfügung stellt. Er wird Ihnen ein Konto erstellen und Ihnen eindeutige Zugangsdaten zukommen lassen.

Um die SMS-Einstellungen in ERPNext zu konfigurieren lesen Sie sich das Hilfe-Dokument zur HTTP API durch (dieses beschreibt die Methode, wie auf die SMS-Schnittstelle über einen Drittparteien-Anbieter zugegriffen werden kann). In diesem Dokument finden Sie eine URL, die dafür benutzt wird eine SMS mithilfe einer HTTP-Anfrage zu versenden. Wenn Sie diese URL benutzen, können Sie die SMS-Einstellungen in ERPNext konfigurieren.

Beispiel-URL:

    
    http://instant.smses.com/web2sms.php?username=<USERNAME>&password;=<PASSWORD>&to;=<MOBILENUMBER>&sender;=<SENDERID>&message;=<MESSAGE>
    
<img class="screenshot" alt="SMS-Einstellungen" src="{{docs_base_url}}/assets/img/setup/sms-settings2.jpg">


> Anmerkung: Die Zeichenfolge bis zum "?" ist die URL des SMS-Gateways.

Beispiel:

http://instant.smses.com/web2sms.php?username=abcd&password;=abcd&to;=9900XXXXXX&sender;=DEMO&message;=THIS+IS+A+TEST+SMS

Die oben angegebene URL verschickt SMS über das Konto "abcd" an Mobilnummern "9900XXXXXX" mit der Sender-ID "DEMO" und der Textnachricht "THIS IS A TEST SMS".

Beachten Sie, dass einige Parameter in der URL statisch sind. Sie bekommen von Ihrem SMS-Anbieter statische Werte wie Benutzername, Passwort usw. Diese statischen Werte sollten in die Tabelle der statischen Parameter eingetragen werden.

<img class="screenshot" alt="SMS-Einstellungen" src="{{docs_base_url}}/assets/img/setup/sms-settings1.png">


{next}
