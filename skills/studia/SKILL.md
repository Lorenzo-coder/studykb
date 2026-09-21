---
name: studia
description: Conduce una sessione di studio su un argomento del master QML usando la knowledge base studykb. Usare quando l'utente dice "studiamo X", cita un codice del piano (A7, C15, F5, H12...), chiede di spiegare un argomento del master, o invoca /studia.
---

# Sessione di studio — master QML Ca' Foscari

Una sessione copre **un argomento solo**. Mai un modulo intero, mai due
argomenti insieme.

## Dove sta il piano

`~/Personale/QML/vault/00-syllabus/00-PIANO-DI-STUDIO.md`

Contiene 184 argomenti, ognuno con un codice (`A1`, `C15`, `F5`, `H12`, ...).
Il codice porta con sé il modulo e la fonte principale. Se l'utente dice un
codice, parti da lì. Se dice un argomento a parole, cerca la riga
corrispondente nel piano prima di fare altro.

## La procedura

1. **Trova l'argomento nel piano.** Prendi il modulo (`M4`, `M7`, ...) e la
   fonte indicata fra parentesi graffe.
2. **Cerca**: `kb_search "<argomento>" module="<Mn>" k=8`. Al massimo otto
   passaggi. Se otto non bastano, l'argomento è troppo largo: dillo all'utente
   e proponi di spezzarlo in due.
3. **Se il materiale è magro**, una seconda ricerca con `type="transcript"`.
   Spesso il docente dice a voce la cosa che la slide si limita a nominare.
4. **Scrivi la nota** in `vault/10-modules/<Mn>/<NN>-<slug>.md`, seguendo
   `studykb/docs/agents/note-synthesis.md`. La spiegazione completa va **qui**,
   nello stile descritto sotto, con LaTeX vero per le formule. Il terminale non
   rende LaTeX, il viewer sì.
5. **In terminale**, in quest'ordine e niente altro:
   - l'URL della nota, `http://127.0.0.1:8077/read#/10-modules/<Mn>/<NN>-<slug>.md`
   - un riassunto da cinque a otto righe, in notazione Unicode
   - una riga che dice cosa c'è nella nota e non nel riassunto
   - **tre domande di verifica**
   Poi fermati e aspetta. Non rispondere tu.
6. **Se le risposte sono giuste**, spunta la casella nel piano. La nota c'è già.
7. **Se le risposte sono sbagliate**, non ripetere la stessa spiegazione con
   parole diverse. Vuol dire che non era chiara: correggi **la nota** partendo
   da un esempio numerico, e ridai l'URL.

Il terminale è il posto del dialogo. Il browser è il posto della lettura.

## Lo stile della spiegazione

Questa è la parte che conta di più. Il modello da imitare è questo, scelto
dall'utente:

> ## L'algoritmo di Grover
>
> **Il problema.** Hai un insieme di N elementi. Non sai come sono ordinati.
> Devi trovare quello che ha una certa proprietà.
>
> **Termine da fissare: oracolo.** È una funzione che, dato un elemento,
> risponde soltanto "sì, è questo" oppure "no". Non ti dice dove si trova.
> Riconoscere la soluzione è facile. Trovarla no.
>
> **Quanto costa senza quantistica.** Non avendo struttura, devi provarli a uno
> a uno. In media N/2 tentativi, nel caso peggiore N. [Nielsen & Chuang p.72]
>
> **Quanto costa con Grover.** Servono circa √N iterazioni. Con N = 1.000.000
> significa passare da un milione di tentativi a mille. [Nielsen & Chuang p.72]
>
> **Attenzione a non confondere.** Il guadagno è quadratico, non esponenziale.
> Shor è esponenziale. Grover no. [p.72]

Le regole che ne discendono:

- **Paragrafi da due a quattro righe.** Ognuno si apre con un'etichetta in
  grassetto che dice cosa c'è dentro.
- **Frasi corte. Una affermazione per frase.** Se una frase contiene due idee,
  diventano due frasi.
- **Ogni termine tecnico va definito la prima volta che compare**, anche se
  sembra ovvio. Usa l'etichetta `**Termine da fissare: <parola>.**`
- **Numeri concreti invece delle formule**, quando si può. "Da un milione di
  tentativi a mille" si capisce; "O(√N)" va scritto dopo, non prima.
- **Ogni affermazione porta la sua citazione** fra parentesi quadre, sulla
  stessa riga. Una frase che non puoi citare non va scritta.
- **Chiudi con l'errore tipico da evitare**, quando ce n'è uno.

## La notazione

Il terminale non renderizza LaTeX. Il viewer del vault sì. Da qui discendono
due regole diverse per due posti diversi.

**In chat solo Unicode.** `|ψ⟩`, `⟨φ|ψ⟩`, `√N`, `⊗`, `Σ`, `∑ᵢ`, `π/4`, `ħ`,
`≈`, `≤`, `→`, `10⁶`, `xᵢ`, `σ_z` si scrive `σz`. Mai `$...$`, mai `\frac`,
mai `\begin{align}`: in terminale restano caratteri di servizio che vanno letti
a mente, ed è esattamente il lavoro che non deve fare chi studia.

**Una formula che non sta su una riga in Unicode non va in chat.** Va nella
nota. La chat dice quale: "la derivazione del diffusore è nella nota, sezione
Worked through".

**Nella nota LaTeX vero**, `$...$` inline e `$$...$$` in display. Il viewer lo
rende con KaTeX. Là dentro non ci sono limiti di notazione.

Resta valida la regola di prima: i numeri concreti vengono prima della formula,
in tutti e due i posti.

## Rigoroso e descrittivo insieme

Sono due requisiti distinti, e il secondo serve a impedire che il primo degeneri.

**Rigoroso** vuol dire questo:

- Ogni numero è misurato o citato, mai stimato a occhio. Se il numero esatto non
  c'è nei passaggi recuperati, scrivi che non c'è invece di arrotondare.
- Distingui sempre cosa dice la fonte da cosa stai deducendo tu. "La slide dice
  X" e "da X segue Y" sono due frasi diverse e vanno tenute separate.
- Le condizioni di validità vanno scritte. Un risultato che vale solo per stati
  puri, o solo per N molto grande, va detto lì, non dopo.
- Se un passaggio della kb è ambiguo, dillo. Non scegliere l'interpretazione più
  comoda in silenzio.

**Descrittivo** vuol dire questo:

Frasi corte **non** significa dire meno cose. Significa dire le stesse cose in
più frasi. La brevità riguarda la singola frase, non il contenuto complessivo.
Se un meccanismo ha tre passaggi, vanno descritti tutti e tre, uno per frase.

Il confronto:

- ✗ **Troppo scarno.** "Il diffusore amplifica. Serve (π/4)√N volte."
- ✓ **Rigoroso e descrittivo.** "Il diffusore riflette tutte le ampiezze attorno
  al loro valore medio. L'oracolo ha appena reso negativa l'ampiezza della
  soluzione, quindi quella riflessione la fa crescere, mentre le altre calano di
  poco. Il ciclo oracolo più diffusore va ripetuto circa (π/4)·√N volte.
  [FCaruso p.87-88]"

La seconda versione ha frasi altrettanto corte. Dice tre cose in più: cosa fa
geometricamente il diffusore, perché il segno negativo è quello che lo fa
funzionare, e che le due operazioni formano un ciclo.

## Cosa non fare

Sono errori ricorrenti di chi scrive queste spiegazioni. L'utente ha detto
esplicitamente che rallentano la lettura.

**Niente frasi aforistiche.**
- ✗ "Invecchia in silenzio."
- ✓ "La documentazione cambia, ma la copia indicizzata resta ferma. Il risultato
  è un passaggio che sembra affidabile e non lo è più."

**Niente contrapposizioni a effetto.**
- ✗ "Era la modifica più piccola, e quella sbagliata."
- ✓ "Convertire in PDF sarebbe stato più rapido. Però perde i timestamp, e i
  timestamp sono il motivo per cui questo estrattore esiste."

**Niente metafore.** Il quantistico ne è già pieno di suo. Aggiungerne altre
confonde invece di chiarire.

**Niente sottintesi.** Se una frase richiede di ricostruire un passaggio
mancante per capirla, quel passaggio va scritto.

**Niente paragrafi lunghi.** Se supera le cinque righe, spezzalo e dai
un'etichetta a ciascun pezzo.

## Come leggere quello che torna dalla kb

Ogni passaggio ha un campo `provenance`. Dice quanto fidarsi.

- **`text-layer`** — letto dal file. Affidabile.
- **`local-vlm`** — è la **descrizione di una figura** scritta da un modello di
  visione da 7 miliardi di parametri. Legge bene le parole, **sbaglia le
  formule**. Non citare mai una formula da qui: scrivi "vedi slide N" e
  rimanda alla pagina.
- **`asr`** / **`asr-corrected`** — trascrizioni delle lezioni. I timestamp
  sono esatti, le parole tecniche possono essere storpiate. Il corso è in
  inglese non madrelingua.

`p.149` è la **pagina del PDF**, il numero da digitare nel visualizzatore. In un
libro con le pagine iniziali romane non coincide con il numero stampato sul
foglio.

## Le lacune vanno dette

Se `kb_search` non trova niente su un punto, **non riempirlo a memoria**.
Scrivilo sotto "Domande aperte". La lacuna è l'informazione utile: dice cosa
chiedere al docente o quale libro aprire.

Tre argomenti del piano sono marcati ⚠️ perché il materiale manca del tutto
(M8 intero, le ultime lezioni di M7, Bell in M3). Su quelli la risposta corretta
è dire che la kb non ha nulla.
