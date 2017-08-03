# Einstandskostenbeleg
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Die Einstandskosten sind der Gesamtbetrag aller Kosten eines Produktes bis es die Tür des Käufers erreicht. Die Einstandskosten umfassen die Originalkosten des Produktes, alle Versandkosten, Zölle, Steuern, Versicherung und Gebühren für Währungsumrechung usw. Es kann sein, dass nicht in jeder Sendung alle diese Komponenten anwendbar sind, aber die zutreffenden Komponenten müssen als Teil der Einstandskosten berücksichtigt werden.

> Um Einstandskosten besser verstehen zu können, lassen Sie uns ein Beispiel aus dem täglichen Leben begutachten. Sie müssen eine neue Waschmaschine für Ihre Wohnung kaufen. Bevor Sie den tatsächlichen Kauf tätigen sehen Sie sich normalerweise ein wenig um, um den besten Preis heraus zu finden. In diesem Prozess haben Sie sicherlich schon oft ein besseres Angebot von einem Geschäft gefunden, das aber weit weg ist. Deshalb sollten Sie also auch die Versandkosten berücksichtigen, wenn Sie bei diesem Geschäft kaufen. Die Gesamtkosten inklusive der Transportkosten könnten höher liegen als der Preis, den Sie im nahegelegenen Laden erhalten. In diesem Fall werden Sie sich wahrscheinlich für den nähesten Laden entscheiden, da die Einstandskosten des Artikels im nahegelegenen Geschäft günstiger sind.

In ähnlicher Art und Weise, ist es sehr wichtig Einstandskosten eines Artikels/Produkts zu identifizieren, weil es dabei hilft den Verkaufspreis dieses Artikels zu bestimmen und sich auf die Profitabilität des Unternehmens auswirkt. Folglich sollten alle zutreffenden Einstandskosten in der Artikelbewertung mit einfliessen.

In Bezugnahme auf die [Third-Party Logistikstudie](http://www.3plstudy.com/) gaben nur 45% der Befragten an, dass Sie die Einstandskosten intensiv nutzen. Der Hauptgrund, warum die Einstandskosten nicht berücksichtigt werden, sind, dass die notwendigen Daten nicht verfügbar sind (49%), es an passenden Werkzeugen fehlt (48%), nicht ausreichend Zeit zur Verfügung steht (31%) und dass nicht klar ist, wie die Einstandskosten behandelt werden sollen (27%).

### Einstandskosten über den Kaufbeleg

In ERPNext können Sie die mit den Einstandskosten verbundenen Abgaben über die Tabelle "Steuern und Abgaben" hinzufügen, wenn Sie einen Kaufbeleg erstellen. Dabei sollten Sie zum Hinzufügen dieser Abgaben die Einstellung "Gesamtsumme und Wert" oder "Bewertung" verwenden. Abgaben, die demselben Lieferanten gezahlt werden müssen, bei dem Sie eingekauft haben, sollten mit "Gesamtsumme und Bewertung" markiert werden. Im anderen Fall, wenn Abgaben an eine 3. Partei zu zahlen sind, sollten Sie mit "Bewertung" markiert werden. Bei der Ausgabe des Kaufbelegs kalkuliert das System die Einstandskosten aller Artikel und berücksichtigt dabei diese Abgabe, und die Einstandskosten werden bei der Berechnung der Artikelwerte berücksichtigt (basierend auf der FIFO-Methode bzw. der Methode des Gleitenden Durchschnitts).

In der Realität aber kann es sein, dass wir beim Erstellen des Kaufbelegs nicht alle für die Einstandskosten anzuwendenden Abgaben kennen. Der Transporteur kann die Rechnung nach einem Monat senden, aber man kann nicht bis dahin mit dem Buchen des Kaufbeleges warten. Unternehmen, die ihre Produkte/Teile importieren, zahlen einen großen Betrag an Zöllen. Und normalerweise bekommen Sie Rechnungen vom Zollamt erst nach einiger Zeit. In diesen Fällen werden Einstandskostenbelege sympathisch, weil sie Ihnen erlauben diese zusätzlichen Abgaben an einem späteren Zeitpunkt hinzuzufügen und die Einstandskosten der gekauften Artikel zu aktualisieren.

### Einstandskostenbeleg

Sie können die Einstandskosten an jedem zukünftigen Zeitpunkt über einen Einstandskostenbeleg aktualisieren.

> Lagerbestand > Werkzeuge > Beleg über Einstandskosten

Im Dokument können Sie verschiedene Kaufbelege auswählen und alle Artikel daraus abrufen. Dann sollten Sie zutreffende Abgaben aus der Tabelle "Steuern und Abgaben" hinzufügen. Die hinzugefügten Abgaben werden proportional auf die Artikel aufgeteilt, basierend auf ihrem Wert.

<img class="screenshot" alt="Einstandskostenbeleg" src="/docs/assets/img/stock/landed-cost.png">

### Was passiert bei der Ausgabe?

1. Bei der Ausgabe des Einstandskostenbelegs werden die zutreffenden Einstandskosten in der Artikelliste des Kaufbelegs aktualisiert.
2. Die Bewertung der Artikel wird basierend auf den neuen Einstandskosten neu berechnet.
3. Wenn Sie die Ständige Inventur nutzen, verbucht das System Buchungen im Hauptbuch um den Lagerbestand zu korrigieren. Es belastet (erhöht) das Konto des zugehörigen Lagers und entlastet (erniedrigt) das Konto "Ausgaben in Bewertung eingerechnet". Wenn Artikel schon geliefert wurden, wurden die Selbstkosten zur alten Bewertung verbucht. Daher werden Hauptbuch-Buchungen erneut für alle zukünftigen ausgehenden Buchungen verbundener Artikel erstellt um den Selbstkosten-Betrag zu korrigieren.

{next}
