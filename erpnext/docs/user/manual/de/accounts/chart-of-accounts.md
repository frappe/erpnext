# Kontenplan
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Der Kontenplan bildet die Blaupause Ihres Unternehmens. Die Rahmenstruktur Ihres Kontenplans basiert auf einem System der doppelten Buchführung, die auf der ganzen Welt zum Standard der finanziellen Bewertung eines Unternehmens geworden ist.

Der Kontenplan hilft Ihnen bei der Beantwortung folgender Fragen:

* Was ist Ihre Organisation wert?
* Wieviele Schulden haben Sie?
* Wieviel Gewinn erwirtschaften Sie (und in diesem Zuge auch, wieviele Steuern zahlen Sie?)
* Wieviel Umsatz generieren Sie?
* Wie setzen sich Ihre Ausgaben zusammen?

Als Manager werden Sie zu schätzen wissen, wenn Sie beurteilen können wie Ihr Geschäft läuft.

> Tipp: Wenn Sie eine Bilanz nicht lesen können (es hat lange gedauert bis wir das konnten), dann ist jetzt eine gute Gelegenheit es zu erlernen. Es wird die Mühe wert sein. Sie können auch die Hilfe Ihres Buchhalters in Anspruch nehmen, wenn Sie Ihren Kontenplan einrichten möchten.

Sie können in ERPNext leicht die finanzielle Lage Ihres Unternehmens einsehen. Ein Beispiel für eine Finanzanalyse sehen Sie unten abgebildet.

<img class="screenshot" alt="Finanzanalyse Bilanz" src="/docs/assets/img/accounts/financial-analytics-bl.png">

Um Ihren Kontenplan in ERPNext zu bearbeiten gehen Sie zu:

> Rechnungswesen > Einstellungen > Kontenplan

Im Kontenplan erhalten Sie eine Baumstruktur der Konten(bezeichnungen) und Kontengruppen, die ein Unternehmen benötigt um seine Buchungsvorgänge vornehmen zu können. ERPNext richtet für jede neu angelegte Firma einen einfachen Kontenrahmen ein, aber Sie müssen noch Anpassungen vornehmen, damit Ihren Anforderungen und gesetzlichen Bestimmungen Genüge geleistet wird. Der Kontenplan gibt für jede Firma an, wie Buchungssätze klassifiziert werden, meistens aufgrund gesetzlicher Vorschriften (Steuern und Einhaltung staatlicher Regelungen).

Lassen Sie uns die Hauptgruppen des Kontenplans besser verstehen lernen.

<img class="screenshot" alt="Kontenplan" src="/docs/assets/img/accounts/chart-of-accounts-1.png">

### Bilanzkonten

Die Bilanz beinhaltet Vermögenswerte (Mittelverwendung) und Verbindlichkeiten (Mittelherkunft), die den Nettowert Ihres Unternehmens zu einem bestimmten Zeitpunkt angeben. Wenn Sie eine Finanzperiode beginnen oder beenden dann ist die Gesamtsumme aller Vermögenswerte gleich den Verbindlichkeiten.

> Buchhaltung: Wenn Sie in Bezug auf Buchhaltung Anfänger sind, wundern Sie sich vielleicht, wie das Vermögen gleich den Verbindlichkeiten sein kann? Das würde ja heißen, dass das Unternehmen selbst nichts besitzt. Das ist auch richtig. Alle Investitionen, die im Unternehmen getätigt werden, um Vermögen anzuschaffen (wie Land, Möbel, Maschinen) werden von den Inhabern getätigt und sind für das Unternehmen eine Verbindlichkeit. Wenn das Unternehmen schliessen möchte, müssen alle Vermögenswerte verkauft werden und die Verbindlichkeiten den Inhabern zurückgezahlt werden (einschliesslich der Gewinne), es bleibt nichts übrig.

So repräsentieren in dieser Sichtweise alle Konten ein Vermögen des Unternehmens, wie Bank, Grundstücke, Geschäftsausstattung, oder eine Verbindlichkeit (Kapital welches das Unternehmen anderen schuldet), wie Eigenkapital und diverse Verbindlichkeiten.

Zwei besondere Konten, die in diesem Zuge angesprochen werden sollten, sind die Forderungen (Geld, welches Sie noch von Ihren Kunden bekommen) und die Verbindlichkeiten (aus Lieferungen und Leistungen) (Geld, welches Sie noch an Ihre Lieferanten zahlen müssen), jeweils dem Vermögen und den Verbindlichkeiten zugeordnet.

### Gewinn- und Verlustkonten

Gewinn und Verlust ist die Gruppe von Ertrags- und Aufwandskonten, die Ihre Buchungstransaktionen eines Zeitraums repräsentieren.

Entgegen den Bilanzkonten, repräsentieren Gewinn und Verlustkonnten (GuV) keine Nettowerte (Vermögen), sondern die Menge an Geld, welche im Zuge von Geschäften mit Kunden in einem Zeitraum ausgegeben oder verdient wird. Deshalb sind sie auch zu Beginn und zum Ende eines Geschäftsjahres gleich 0.

In ERPNext ist es einfach eine graphische Auswertung von Gewinn und Verlust zu erstellen. Im Folgenden ist ein Beispiel einer GuV-Analyse abgebildet:

<img class="screenshot" alt="Finanzanalyse GuV" src="/docs/assets/img/accounts/financial-analytics-pl.png">

(Am ersten Tag eines Jahres haben Sie noch keinen Gewinn oder Verlust gemacht, aber Sie haben bereits Vermögen, deshalb haben Bestandskonten zum Anfang oder Ende eines Zeitraums einen Wert.)

### Gruppen und Hauptbücher

Es gibt in ERPNext zwei Hauptgruppen von Konten: Gruppen und Bücher. Gruppen können Untergruppen und Bücher haben, wohingegen Bücher die Knoten Ihres Plans sind und nicht weiter unterteilt werden können.

Buchungstransaktionen können nur zu Kontobüchern erstellt werden (nicht zu Gruppen).

> Info: Der Begriff "Hauptbuch" bezeichnet eine Aufzeichnung, in der Buchungen verzeichnet sind. Normalerweise gibt es für jedes Konto (wie z. B. einem Kunden oder Lieferanten) nur ein Buch.

> Anmerkung: Ein Kontenbuch wird manchmal auch als Kontokopf bezeichnet.

<img class="screenshot" alt="Kontenplan" src="/docs/assets/img/accounts/chart-of-accounts-2.png">

### Andere Kontentypen

Wenn sie in ERPNext ein neues Konto anlegen, können Sie dazu auch Informationen mit angeben, und zwar deshalb, weil es eine Hilfe sein kann, in einem bestimmte Szenario, ein bestimmtes Konto, wie Bankkonto ein Steuerkonto, auszuwählen. Das hat auf den Kontenrahmen selbst keine Auswirkung.

### Konten erstellen und bearbeiten

Um ein neues Konto zu erstellen, gehen Sie Ihren Kontenplan durch und klicken Sie auf die Kontengruppe unter der Sie das neue Konto erstellen wollen. Auf der rechten Seite finden Sie die Option ein neues Konto zu "öffnen" oder ein Unterkonto zu erstellen.

<img class="screenshot" alt="Kontenplan" src="/docs/assets/img/accounts/chart-of-accounts-3.png">

Die Option zum Erstellen erscheint nur dann, wenn Sie auf ein Konto vom Typ Gruppe (Ordner) klicken.

ERPNext legt eine Standardkontenstruktur an, wenn eine Firma angelegt wird. Es liegt aber an Ihnen, Konten zu bearbeiten, hinzuzufügen oder zu löschen.

Typischerweise werden Sie vielleicht Konten hierfür anlegen wollen:

* Aufwandskonten (Reisen, Gehälter, Telefon) unter Aufwände
* Steuern (Mehrwertsteuer, Verkaufssteuer je nach Ihrem Land) unter kurzfristige Verbindlichkeiten
* Verkaufsarten (z. B. Produktverkäufe, Dienstleistungsverkäufe) unter Erträge
* Vermögenstypen (Gebäude, Maschinen, Geschäftsausstattung) unter Anlagevermögen

{next}
