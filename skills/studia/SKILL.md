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
Il codice porta con sé il modulo e la fonte del corso. Se l'utente dice un
codice, parti da lì. Se dice un argomento a parole, cerca la riga
corrispondente nel piano prima di fare altro.

## Due livelli di fonti

La kb è divisa in due, e i due livelli hanno ruoli diversi.

**Gold: libri e paper** (`type="book"`, `type="paper"`). Sono il patrimonio da
cui si prende il contenuto. La spiegazione si costruisce su di loro,
rielaborata, non parafrasata frase per frase. Possono andare oltre il corso: va
bene, purché si dica che è oltre.

**Corso: slide e trascrizioni** (`type="slides"`, `type="transcript"`). Servono
a due cose sole. Primo, non lasciare indietro niente di quello che è stato
fatto a lezione. Secondo, non gonfiare la nota con cose che il corso non ha
toccato e che non servono all'argomento. Da qui si prende anche la notazione
usata dal docente, se diversa da quella del libro.

**Eccezione da ricordare.** In `papers/` ci sono anche dispense e materiale dei
docenti: `Lecture4 (spins_and_qubits)`, `lectures_master_spin_qubit`,
`lecture_angular_momentum`, `lecture_QM_formalism`, `lectures_formalism1`,
`potential_well`, `proof_operators`, `complex_numbers`, `exercise*`,
`exercises*`, `Assessment*`. Risultano `type="paper"` e restano così: le
dispense sono affidabili e valgono come gold, citate come "dispensa <autore>".
Gli `Assessment` sono domande d'esame: si usano al passo 4, non come contenuto.

## La procedura

1. **Trova l'argomento nel piano.** Prendi il modulo e la fonte del corso.
2. **Gold**: `kb_search "<argomento>" type="book" k=8`, **senza** filtro di
   modulo: un libro può trattare l'argomento anche se è assegnato a un altro
   modulo. Nielsen & Chuang, Schuld & Petruccione e le dispense sono i primi da
   guardare. Se serve, una seconda ricerca con `type="paper"`.
3. **Corso**: `kb_search "<argomento>" module="<Mn>" k=8` per sapere cosa è
   stato fatto a lezione e con quale notazione. Una ricerca `type="transcript"`
   solo se le slide sono magre.
4. **Esame**: se l'argomento è di un modulo già esaminato (M1–M6),
   `kb_search "<argomento>" source="Assessment" k=4`. Le domande vere d'esame
   dicono cosa il corso considera essenziale.
5. **Se la nota esiste già** (dal 26/09/2026 esistono quelle di tutti i blocchi
   del calendario, con le domande in fondo), non riscriverla: rileggila, dai
   l'URL e parti dalle sue "Domande di verifica". Correggila solo se le
   risposte mostrano che non è chiara (passo 8).
   **Altrimenti scrivi la nota** in `vault/10-modules/<Mn>/<NN>-<slug>.md`, con la
   struttura descritta sotto, e con una figura se una fonte ne ha una (vedi
   "Le figure"). Questa struttura prevale su
   `studykb/docs/agents/note-synthesis.md`.
6. **Rispondi dove è arrivata la domanda.** Se l'utente ha scritto in terminale,
   rispondi in terminale. Se ha scritto nella chat della pagina, rispondi lì e
   in terminale scrivi solo una riga con l'URL. Il contenuto della risposta è
   sempre questo, in quest'ordine e niente altro:
   - l'URL della nota, `http://127.0.0.1:8077/read#/10-modules/<Mn>/<NN>-<slug>.md`
   - un riassunto da cinque a otto righe
   - una riga che dice cosa c'è nella nota e non nel riassunto
   - **tre domande di verifica**, di cui almeno una sulla realizzazione fisica
     e, se esiste, una nello stile delle domande d'esame
   Poi fermati e aspetta. Non rispondere tu.
7. **Se le risposte sono giuste**, spunta la casella nel piano.
8. **Se le risposte sono sbagliate**, non ripetere la stessa spiegazione con
   parole diverse. Vuol dire che non era chiara: correggi **la nota** partendo
   da un esempio numerico, e ridai l'URL.

Budget: al massimo otto passaggi per ricerca, al massimo quattro ricerche. Se
non bastano, l'argomento è troppo largo: dillo e proponi di spezzarlo.

## La chat della pagina

La pagina `http://127.0.0.1:8077/read` ha una chat. Quello che l'utente scrive
lì finisce in `~/Personale/QML/vault/.chat.jsonl`, una riga JSON per messaggio,
e **nient'altro**: il server non lo inoltra a nessuno. Se la sessione non
ascolta il file, il messaggio resta lì senza risposta.

**Primo passo di ogni sessione, prima di tutto il resto:**

1. **Guarda se c'è un messaggio in attesa.** `tail -n 1` del file: se l'ultima
   riga ha `"who": "you"`, è una domanda rimasta senza risposta. Parti da quella.
2. **Avvia l'ascolto** con il tool Monitor (caricalo con ToolSearch se è
   differito):
   ```bash
   tail -n 0 -F ~/Personale/QML/vault/.chat.jsonl | grep --line-buffered '"who": "you"'
   ```
   `-n 0` è voluto: arrivano solo i messaggi nuovi, mai lo storico. Rileggere il
   file intero a ogni messaggio costerebbe token per niente.
3. **Rispondi sulla pagina** quando la domanda arriva da lì. Scrivi la risposta
   in un file nello scratchpad e mandala così, per non combattere con le
   virgolette:
   ```bash
   curl -s -X POST 'http://127.0.0.1:8077/chat?who=claude' --data-binary @risposta.md
   ```
   La chat della pagina rende Markdown **e** LaTeX (KaTeX, `$...$` e `$$...$$`):
   la regola "solo Unicode" vale per il terminale, non qui.

## Lo stile: la scuola di Landau

Il modello è il Corso di fisica teorica di Landau e Lifshitz (i PDF sono in
`kb/books/` ma esclusi dall'indice nel MANIFEST). Rigoroso, conciso, chiaro, niente lasciato al caso. In pratica:

- **Si parte dal fatto fisico, non dalla formula.** Prima cosa si osserva, poi
  l'oggetto matematico che lo descrive, poi le conseguenze. La matematica è
  introdotta perché serve, e si dice a cosa serve.
- **Ogni passaggio è giustificato.** Un risultato o si deriva, mostrando i
  passaggi, o si cita. Mai "si può mostrare che" senza l'uno o l'altro.
- **Niente di ridondante.** Ogni frase dice una cosa nuova. Niente ripetizioni
  del titolo, niente annunci ("ora vedremo"), niente riassunti a metà testo.
- **Definizioni precise**, date una volta sola, nel punto in cui servono, in un
  blocco `**Definizione.**`. Ogni simbolo è definito prima di essere usato.
- **Condizioni di validità scritte nel punto in cui valgono.** "Solo per stati
  puri", "solo per un qubit", "solo per N grande": lì, non dopo.
- **Equazioni numerate** (`\tag{1}`) quando vengono richiamate più avanti.
- **Numeri concreti.** Dopo ogni risultato generale, un caso numerico che lo
  rende tangibile.

Conciso non vuol dire allusivo. Un passaggio che il lettore deve ricostruire da
solo va scritto. Chi legge non ha la base di matematica (la parte A del piano è
saltata): i prerequisiti vanno richiamati in una riga dove servono.

**Modello da imitare** (tono e densità, non contenuto da copiare):

> ### §1. Il fatto sperimentale
>
> Luce polarizzata a 45° incide su un polarizzatore orizzontale. Passa metà
> dell'intensità: è la legge di Malus, $I = I_0\cos^2\theta$ con $\theta = 45°$.
> Si riduca l'intensità fino a mandare un fotone alla volta. Un rivelatore dopo
> il polarizzatore non registra mai "mezzo fotone": ogni fotone passa intero o
> non passa. Su molti fotoni ne passa la metà.
>
> Ne segue che il singolo fotone non ha una polarizzazione orizzontale o
> verticale già definita prima della misura. Ha soltanto una probabilità, 1/2,
> di essere trovato orizzontale.
>
> ### §2. Lo stato
>
> **Definizione.** Lo stato di polarizzazione è un vettore
> $|\psi\rangle = \alpha|H\rangle + \beta|V\rangle$ di uno spazio complesso a due
> dimensioni, dove $|H\rangle$ e $|V\rangle$ sono le due polarizzazioni che il
> polarizzatore distingue con certezza.
>
> La probabilità di trovare $H$ è $|\alpha|^2$. Poiché il fotone è trovato
> sempre in uno dei due stati, $|\alpha|^2 + |\beta|^2 = 1$. Per il fotone a
> 45°, $\alpha = \beta = 1/\sqrt2$, e $|\alpha|^2 = 1/2$ riproduce il §1.

## La struttura della nota

```markdown
# <Argomento>

> <Mn> · <docente> · piano <codice>

**Prerequisiti.** <cosa si assume, una riga, con link alle note precedenti>

## §1. <il fatto fisico o il problema da cui si parte>
## §2. ... <sviluppo: definizioni, derivazioni, risultati, in ordine logico>

## Realizzazione fisica
<un sistema concreto: fotone, spin 1/2, atomo a due livelli, qubit
superconduttore. Ogni oggetto matematico messo in corrispondenza con una cosa
misurabile: cos'è lo stato, cos'è la base, cosa fa l'apparato di misura, che
numeri escono. Con numeri.>

## Esempio numerico
<un calcolo svolto dall'inizio alla fine>

## Nel corso
<cosa è stato fatto a lezione, con quale notazione; cosa nella nota va oltre il
corso; cosa hanno chiesto all'esame. Qui vanno le citazioni di slide e
trascrizioni.>

## Errore tipico
## Domande aperte
## Fonti
<prima i gold, poi il corso>
```

La **realizzazione fisica** è obbligatoria per ogni argomento che descrive un
sistema quantistico (parti D, E, G e, dove ha senso, F). Per gli argomenti
puramente matematici o di ML si omette.

## Le citazioni

- **Poche e mirate.** Una citazione gold per risultato o per sezione, non una
  per frase. Si citano i postulati, i fatti sperimentali, i risultati non
  derivati nella nota. Un risultato derivato passo per passo nella nota non ha
  bisogno di citazione: la derivazione è la sua prova.
- **Slide e trascrizioni si citano solo nella sezione "Nel corso"**, tranne
  quando il corso aggiunge qualcosa che nei gold non c'è.
- **Nessuna affermazione inventata.** Ogni frase è citata, derivata nella nota,
  oppure marcata `(fuori kb)` se è fisica standard assente dalla kb. `(fuori kb)`
  è ammesso solo per la realizzazione fisica e per richiami di prerequisiti, e i
  numeri devono essere esatti.

## Le figure

Una figura entra nella nota **solo se esiste già in una fonte**. Mai generarla,
mai disegnarla: se non c'è, la nota resta senza.

1. **Trovala.** Nei libri la legenda della figura è nel testo: cerca
   `"Figure <argomento>"` con `source=` sul libro. Nelle slide cerca con
   `type="caption"`: le didascalie del modello di visione dicono quali pagine
   hanno un disegno.
2. **Ritagliala** dalla directory `~/Personale/studykb`:
   ```bash
   uv run studykb figure "<parte del nome>" <pagina> --corpus qml-master --root ~/Personale/QML/kb
   uv run studykb figure Nielsen 49 --clip 0.28,0.40,0.72,0.69 --corpus qml-master --root ~/Personale/QML/kb
   ```
   Senza `--clip` esce la pagina intera; va bene per una slide. Per un libro
   ritaglia: `x0,y0,x1,y1` in frazioni della pagina, legenda inclusa. Il file
   finisce in `vault/assets/`.
3. **Guardala** con Read prima di inserirla: una sola volta, per controllare
   che sia la figura giusta e che il taglio non mozzi etichette. Se non va,
   correggi `--clip` e rilancia: il file viene sovrascritto.
4. **Inseriscila** con il percorso relativo alla nota e la citazione sotto:
   ```markdown
   ![Sfera di Bloch](../../assets/michael-a-nielsen-isaac-l-chuang-quantum-p49-clip.png)
   *Nielsen & Chuang, Fig. 1.3, p.49*
   ```

Al massimo due figure per nota: una gold nel corpo, una del corso in "Nel
corso" se usa una notazione diversa. Il testo resta completo anche senza
figura: la figura mostra, non spiega.

## La notazione

**In terminale solo Unicode.** `|ψ⟩`, `⟨φ|ψ⟩`, `√N`, `⊗`, `Σ`, `π/4`, `ħ`,
`≈`, `→`, `10⁶`, `xᵢ`, `σz`. Mai `$...$` in terminale. Una formula che non sta
su una riga in Unicode va nella nota, e il terminale dice in quale sezione.

**Nella nota e nella chat della pagina LaTeX vero**, `$...$` inline e `$$...$$`
in display. Dentro le tabelle Markdown usare `\vert` al posto di `|`.

## Cosa non fare

- **Niente frasi aforistiche** ("invecchia in silenzio").
- **Niente contrapposizioni a effetto** ("era la modifica più piccola, e quella
  sbagliata").
- **Niente metafore.** L'esempio fisico sostituisce la metafora: è un sistema
  vero, non un'immagine.
- **Niente sottintesi.** Se una frase richiede di ricostruire un passaggio
  mancante, quel passaggio va scritto.
- **Niente paragrafi oltre le cinque righe.**

## Come leggere quello che torna dalla kb

Ogni passaggio ha un campo `provenance`.

- **`text-layer`** — letto dal file. Affidabile per il testo. **Attenzione: le
  equazioni in display spesso mancano** e al loro posto ci sono righe vuote
  (succede in Nielsen & Chuang e nelle dispense LaTeX). **Si ricostruiscono.**
  Il testo attorno di solito nomina le grandezze e dice cosa fa l'equazione
  ("we may rewrite Eq. 1.1 as ... where θ, φ, γ are real"). Si scrive
  l'equazione e la si verifica: coerenza con il testo prima e dopo, con le
  definizioni, e dove si può con un caso numerico. Se l'equazione è un
  risultato, meglio derivarla nella nota. Se il contesto non la determina in
  modo univoco (convenzioni di segno, di normalizzazione, di ordine), scrivi
  quale convenzione hai scelto e aggiungi "da confrontare con p.N".
- **`local-vlm`** — descrizione di una figura scritta da un modello di visione
  da 7B. Legge bene le parole, **sbaglia le formule**. Non citarne mai una
  formula: rimanda alla pagina.
- **Trascrizioni** (`type="transcript"`). Quelle del corso sono resoconti già
  scritti in prosa, con locator `¶N-M`, e risultano `text-layer`. Si citano
  come "Lezione NN ¶N-M". Solo i sottotitoli grezzi (`.vtt`, `.srt`, Teams con
  orari) sono `asr` / `asr-corrected`: timestamp esatti, parole tecniche a
  volte storpiate, inglese non madrelingua.

`p.149` è la **pagina del PDF**, non quella stampata.

## Le lacune vanno dette

Se la kb non ha niente su un punto e il punto non è fisica standard da
realizzazione fisica, non riempirlo a memoria: va sotto "Domande aperte".

Tre argomenti del piano sono marcati ⚠️ perché il materiale del corso manca
(M8 intero, le ultime lezioni di M7, Bell in M3). Lì il corso non dice nulla, ma
i gold possono coprire l'argomento: dillo esplicitamente.
