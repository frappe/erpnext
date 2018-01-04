# Vertriebseinstellungen
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

In den Vertriebseinstellungen können Sie Eigenheiten angeben, die bei Ihren Vertriebstransaktionen mit berücksichtigt werden. Im Folgenden sprechen wir jeden einzelnen Punkt an.

<img class="screenshot" alt="Vertriebseinstellungen" src="/docs/assets/img/selling/selling-settings.png">

### 1\. Benennung der Kunden nach

Wenn ein Kunde abgespeichert wird, generiert das System eine einzigartige ID für diesen Kunden. Wenn Sie diese Kunden-ID verwenden, können Sie einen Kunden in einer anderen Transaktion auswählen.

Als Standardeinstellung wird der Kunde mit dem Kundennamen abgespeichert. When Sie möchten, dass der Kunde unter Verwendung eines Nummernkreises abgespeichert wird, sollten Sie "Benennung der Kunden nach" auf "Nummernkreis" einstellen.

Hier ein Beispiel für Kunden-IDs, die über einen Nummernkreis abgespeichert werden: `CUST00001, CUST00002, CUST00003 ...` und so weiter.

Sie können den Nummernkreis für die Kundenbenennung wie folgt einstellen:

> Einstellungen > Einstellungen > Nummernkreis

### 2\. Benennung der Kampagnen nach

Genauso wie für den Kunden, können Sie für die Kampagnenstammdaten einstellen, wie eine ID generiert wird. Standardmäßig wird eine Kampagne mit dem Kampagnennamen abgespeichert, wie es vom System während der Erstellung angeboten wird.

### 3\. Standardkundengruppe

Die Kundengruppe in diesem Feld wird automatisch aktualisiert, wenn Sie ein Neukundenformular öffnen. Wenn Sie das Angebot für einen Lead in eine Kundenbestellung umwandeln, versucht das System im Hintergrund den Lead in einen Kunden umzuwandeln. Während im Hintergrund der Kunde erstellt wird, müssen für das System die Kundengruppe und die Region in den Verkaufseinstellungen angegeben werden. Wenn das System keine Einträge findet, wird eine Nachricht zur Bestätigung ausgegeben. Um dies zu verhindern, sollten Sie entweder einen Lead manuell in einen Kunden umwandeln und die Kundengruppe und die Region manuell angeben während der Kunde erstellt wird, oder eine Standardkundengruppe und eine Region in den Vertriebseinstellungen hinterlegen. Dann wird der Lead automatisch in einen Kunden umgewandelt, wenn Sie ein Angebot in eine Kundenbestellung umwandeln.

### 4\. Standardregion
Die Region, die in diesem Feld angegeben wird, wird automatisch im Feld "Region" im Kundenstamm eingetragen.
Wie in der Kundengruppe, wird die Region auch angefragt, wenn das System im Hintergrund versucht einen Kunden anzulegen.

### 5\. Standardpreisliste
Die Preisliste, die in diesem Feld eingetragen wird, wird automatisch in das Preislistenfeld bei Vertriebstransaktionen übernommen.

### 6\. Kundenauftrag erforderlich
Wenn Sie möchten, dass die Anlage eines Kundenauftrages zwingend erforderlich ist, bevor eine Ausgangsrechnung erstellt wird, dann sollten Sie im Feld "Kundenauftrag benötigt" JA auswählen. Standardmäßig ist der Wert auf NEIN voreingestellt.

### 7\. Lieferschein erforderlich
Wenn Sie möchten, dass die Anlage eines Lieferscheins zwingend erforderlich ist, bevor eine Ausgangsrechnung erstellt wird, dann sollten Sie im Feld "Lieferschein benötigt" JA auswählen. Standardmäßig ist der Wert auf NEIN voreingestellt.

### 8\. Gleiche Preise während des gesamten Verkaufszyklus beibehalten
Das System geht standardmäßig davon aus, dass der Preis während des gesamten Vertriebszyklus (Kundenbestellung - Lieferschein - Ausgangsrechnung) gleich bleibt. Wenn Sie bemerken, dass sich der Preis währen des Zyklus ändern könnte, und Sie die Einstellung des gleichbleibenden Preises umgehen müssen, sollten Sie dieses Feld deaktivieren und speichern.

### 9\. Benutzer erlauben, die Preisliste zu Transaktionen zu bearbeiten
Die Artikeltabelle einer Vertriebstransaktion hat ein Feld, das als Preislisten-Preis bezeichnet wird. Dieses Feld kann standardmäßig in keiner Vertriebstransaktion bearbeitet werden. Damit wird sicher gestellt, dass der Preis für alle Artikel aus dem Datensatz für den Artikelpreis erstellt wird, und der Benutzer keine Möglichkeit hat, hier einzuwirken.
Wenn Sie einem Benutzer ermöglichen müssen, den Artikelpreis, der aus der Preisliste gezogen wird, zu ändern, sollten Sie dieses Feld deaktivieren.
