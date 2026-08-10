import streamlit as st

def render():
    
    st.subheader("RSML Tag Reference")
    
    with st.expander("Isolated Tags (hesitations, paralinguistics, other)", expanded=False):
        st.markdown("""
**Hesitations**
`@umm, @uhh, @hmm, @ugh, @huh, @tsk, @uh-huh, @ehh`

**Paralinguistic sounds**
`@laughter, @cry, @hum, @breathe, @sniff, @nose-blowing, @cough, @sneeze, @throat-clearing, @yawn, @eating-sounds, @snore, @groan, @sigh`

**Other**
`@silence, @unintelligible, @stutter-block`
        """)

    with st.expander("Span-based Tags (disfluency / paralinguistic / prosody)", expanded=False):
        st.markdown("""
**Disfluencies** — `@name-start ... @name-end`
`@filler-start ... @filler-end, @repetition-start ... @repetition-end, @broken-word-start ... @broken-word-end, @repair-start ... @repair-end, @false-start-start ... @false-start-end, @prolongation-start ... @prolongation-end`

**Paralinguistics (span form)**
`@crying-start ... @crying-end, @yelling-start ... @yelling-end, @laughing-start ... @laughing-end, @singing-start ... @singing-end, @humming-start ... @humming-end, @whistling-start ... @whistling-end, @whispering-start ... @whispering-end`

**Prosody**
`@emphasis-start ... @emphasis-end, @falling-pitch-start ... @falling-pitch-end, @raising-pitch-start ... @raising-pitch-end`

**Speaker turns** — `&sN-start ... &sN-end`
E.g., `&s1-start` for speaker 1, `&s2-start` for speaker 2.
        """)

    with st.expander("Named Entities Tagset", expanded=False):
        st.markdown("""
| Tag | Name | Example |
|---|---|---|
| `#PER[...](...)` | Person | `#PER[रमेश](रमेश)` |
| `#GPE[...](...)` | Geo Political Entity | `#GPE[नई ढिल्ली](नई दिल्ली)` |
| `#FAC[...](...)` | Facility | `#FAC[रेल निलय](रेल निलय)` |
| `#LOC[...](...)` | Location | `#LOC[ఎంజీ రోడ్డు](MG Road)` |
| `#ITEM[...](...)` | Item | `#ITEM[टिकट](ticket)` |
| `#WOA[...](...)` | Work of Art | `#WOA[त्त्री इडियट्स](3 Idiots)` |
| `#EVENT[...](...)` | Event | `#EVENT[दीवाली](दीवाली)` |
| `#SPORTS[...](...)` | Sports | `#SPORTS[क्रिकेट](Cricket)` |
| `#ORG[...](...)` | Organization | `#ORG[ट्र्रिपल आइटी](IIIT)` |
| `#BRAND[...](...)` | Brand | `#BRAND[स्विग्गी](Swiggy)` |
| `#HON[...](...)` | Honorific | `#HON[काका](काका)` |
| `#DATETIME[...](...)` | Date/Time | `#DATETIME[उन्नीस सौ पचासी](1985)` |
| `#MONEY[...](...)` | Money | `#MONEY[दो सौ रुपये](₹200)` |
| `#QUANT[...](...)` | Quantity | `#QUANT[दो टिकट](2 ticket)` |
| `#NUM[...](...)` | Number | `#NUM[सेवंटी पैव](seventy five)` |
| `#LANG[...](...)` | Language | `#LANG[ఇంగ్లీషు](English)` |
| `#LAW[...](...)` | Law/Policy | `#LAW[आरटीई एक्ट](RTE Act)` |
| `#ID[...](...)` | Identifier | `#ID[एबीसीडी1234ई](ABCD1234E)` |
        """)

    with st.expander("Language Codes Reference", expanded=False):
        st.markdown("""
**Format:** `!langcode[spoken](normalized)` (e.g. `!en[హలో](hello)`)

`en` (English), `hi` (Hindi), `bn` (Bengali), `mr` (Marathi), `te` (Telugu), `ta` (Tamil), `gu` (Gujarati), `ur` (Urdu), `kn` (Kannada), `or` (Odia), `ml` (Malayalam), `pa` (Punjabi), `as` (Assamese), `mai` (Maithili), `sat` (Santali), `ks` (Kashmiri), `ne` (Nepali), `sd` (Sindhi), `doi` (Dogri), `kok` (Konkani), `mni` (Manipuri), `brx` (Bodo), `sa` (Sanskrit)
        """)
