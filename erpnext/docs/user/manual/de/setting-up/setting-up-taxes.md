# Steuern einrichten
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Eine der hauptsächlichen Antriebskräfte für die zwingende Verwendung des Buchhaltungswerkzeuges ist die Kalkulation von Steuern. Egal ob Sie Geld verdienen oder nicht, Ihre Regierung tut es (und hilft damit Ihrem Land sicher und wohlhabend zu sein). Und wenn Sie Ihre Steuern nicht richtig berechnen, dann ist sie sehr unglücklich. Gut, lassen wir die Philosophie mal beiseite. ERPNext ermöglicht es Ihnen konfigurierbare Steuervorlagen zu erstellen, die Sie bei Ihren Ver- und Einkäufen verwenden können.

### Steuerkonten

Steuerkonten, die Sie in der Steuervorlage verwenden möchten, müssen Sie im Kontenplan als "Steuer" markieren.

### Artikelsteuer

Wenn einige Ihrer Artikel einer anderen Besteuerung unterliegen als andere, geben Sie diese in der Artikelsteuer-Tabelle an. Auch dann, wenn Sie Ihre Verkaufs- und Einkaufssteuern als Standardsteuersätze hinterlegt haben, verwendet das System für Kalkulationen den Artikelsteuersatz. Die Artikelsteuer hat Vorrang gegenüber anderen Verkaufs- oder Einkaufssteuern. Wenn Sie jedoch die Standard-Verkaufs- und Einkaufssteuern verwenden wollen, geben Sie bitte keine Artikelsteuer in den Artikelstammdaten an. Dann entscheidet sich das System für die Verkaufs- und Einkaufssteuersätze, die Sie als Standardsätze festgelegt haben.

Die Tabelle zu den Artikelsteuern ist ein Abschnitt in den Artikelstammdaten.

<img class="screenshot" alt="Artikelsteuer" src="/docs/assets/img/taxes/item-tax.png">

* **Inklusive oder Exklusive Steuer:** ERPNext erlaubt es Ihnen Artikelpreise inklusive Steuer einzugeben.

<img class="screenshot" alt="Steuer inklusive" src="/docs/assets/img/taxes/inclusive-tax.png">

* **Ausnahme von der Regel:** Die Einstellungen zur Artikelsteuer werden nur dann benötigt, wenn sich der Steuersatz eines bestimmten Artikels von demjenigen, den Sie im Standard-Steuerkonto definiert haben, unterscheidet.
* **Die Artikelsteuer kann überschrieben werden:** Sie können den Artikelsteuersatz überschreiben oder ändern, wenn Sie in der Artikelsteuertabelle zu den Artikelstammdaten gehen.

### Vorlage für Verkaufssteuern und -abgaben

Normalerweise müssen Sie die von Ihren Kunden an Sie gezahlten Steuern sammeln und an den Staat abführen. Manchmal kann es vorkommen, dass Sie mehrere unterschiedliche Steuern an verschiedene Staatsorgane abführen müssen, wie z. B. an Gemeinden, Bund, Länder oder europäische Organisationen.

ERPNext ermittelt Steuern über Vorlagen. Andere Arten von Abgaben, die für Ihre Rechnungen Relevanz haben (wie Versandgebühren, Versicherung, etc.) können genauso wie Steuern eingestellt werden.

Wählen Sie eine Vorlage und passen Sie diese gemäß Ihren Wünschen an.

Um eine neue Vorlage zu einer Verkaufssteuer z. B. mit dem Namen Vorlage für Verkaufssteuern und -abgaben zu erstellen, gehen Sie zu:

> Einstellungen > Rechnungswesen > Vorlage für Verkaufssteuern und -abgaben

<img class="screenshot" alt="Vorlage für Verkaufssteuern" src="/docs/assets/img/taxes/sales-tax-master.png">

Wenn Sie eine neue Vorlage erstellen, müssen Sie für jeden Steuertyp eine neue Zeile einfügen.

Der Steuersatz, den Sie hier definieren, wird zum Standardsteuersatz für alle Artikel. Wenn es Artikel mit davon abweichenden Steuersätzen gibt, müssen Sie in den Stammdaten über die Tabelle Artikelsteuer hinzugefügt werden.

In jeder Zeile müssen Sie folgendes angeben:

* Typ der Kalulation:

    * Auf Nettosumme: Hier wird auf Basis der Nettogesamtsumme (Gesamtbetrag ohne Steuern) kalkuliert.
    * Auf vorherige Zeilensumme/vorherigen Zeilenbetrag: Sie können Steuern auf Basis der vorherigen Zeilensumme/des vorherigen Zeilenbetrags ermitteln. Wenn Sie diese Option auswählen, wird die Steuer als Prozenzsatz der vorherigen Zeilensumme/des vorherigen Zeilenbetrags (in der Steuertabelle) angewandt. "Vorheriger Zeilenbetrag" meint hierbei einen bestimmten Steuerbetrag. Und "Vorherige Zeilensumme" bezeichnet die Nettosumme zuzüglich der zutreffenden Steuern in dieser Zeile. Geben Sie über das Feld "Zeile eingeben" die Zeilennummer an auf die die aktuell ausgewählte Steuer angewendet werden soll. Wenn Sie die Steuer auf die dritte Zeile anwenden wollengeben Sie im Eingabefeld "3" ein.

    * Geben Sie in die Spalte "Satz" den aktuellen Wert für den Steuersatz ein.
 
* Kontenbezeichnung: Die Bezeichnung des Kontos, unter dem diee Steuer verbucht werden soll.
* Kostenstelle: Wenn es sich bei der Steuer/Abgabe um einen Ertrag handelt (wie z. B. die Versandgebühren) muss sie zu einer Kostenstelle gebucht werden.
* Beschreibung: Beschreibung der Steuer (wird in Rechnungen und Angeboten angedruckt)
* Satz: Steuersatz
* Betrag: Steuerbetrag
* Gesamtsumme: Gesamtsumme bis zu diesem Punkt.
* Zeile eingeben: Wenn die Kalkulation auf Basis "vorherige Zeilensumme" erfolgt, können Sie die Zeilennummer auswählen, die für die Kalkulation zugrunde gelegt wird (Standardeinstellung ist hier die vorhergehende Zeile).
* Ist diese Steuer im Basissatz enthalten?: Wenn Sie diese Option ankreuzen heißt das, dass diese Steuer nicht am Ende der Artikeltabelle angezeigt wird, aber Ihrer Hauptartikeltabelle miteinbezogen wird. Dies ist dann nützlich, wenn Sie Ihrem Kunden einen runden Preis geben wollen (inklusive aller Steuern).

Wenn Sie Ihre Vorlage eingerichtet haben, können Sie diese in Ihren Verkaufstransaktionen auswählen.

### Vorlage für Einkaufssteuern und -abgaben

Die Vorlage für Einkaufssteuern und -abgaben ist ähnlich der Vorlage für Verkaufssteuern und -abgaben.

Diese Steuervorlage verwenden Sie für Lieferantenaufträge und Eingangsrechnungen. Wenn Sie mit Mehrwertsteuern (MwSt) zu tun haben, bei denen Sie dem Staat die Differenz zwischen Ihren Eingangs- und Ausgangssteuern zahlen, können Sie das selbe Konto wie für Verkaufssteuern verwenden.

Die Spalten in dieser Tabelle sind denen in der Vorlage für Verkaufssteuern und -abgaben ähnlich mit folgendem Unterschied.

Steuern oder Gebühren berücksichtigen für: In diesem Abschnitt können Sie angeben, ob die Steuer/Abgabe nur für die Bewertung (kein Teil der Gesamtsumme) oder nur für die Gesamtsumme (fügt dem Artikel keinen Wert hinzu) oder für beides wichtig ist.

{next}
