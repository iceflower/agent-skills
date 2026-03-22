# PDF Libraries Comparison

## Overview

Choosing the right PDF library depends on the programming language, use case (read vs write vs transform), and licensing requirements.

## Java / JVM Libraries

### Apache PDFBox

| Aspect | Details |
| --- | --- |
| Language | Java |
| License | Apache License 2.0 |
| Primary Use | Read, write, manipulate PDF documents |
| Strengths | Full-featured, open-source, active community |

Key capabilities:

- Text extraction (with positional information)
- PDF creation and modification
- Form filling (AcroForms)
- Digital signatures
- PDF/A validation (with preflight module)
- Image extraction

```java
// Text extraction example
try (PDDocument document = Loader.loadPDF(new File("input.pdf"))) {
    PDFTextStripper stripper = new PDFTextStripper();
    stripper.setStartPage(1);
    stripper.setEndPage(5);
    String text = stripper.getText(document);
}
```

### iText (iText 7+)

| Aspect | Details |
| --- | --- |
| Language | Java, .NET |
| License | AGPL 3.0 (open-source) / Commercial |
| Primary Use | PDF creation, manipulation, signing |
| Strengths | Production-grade, extensive API, strong PDF standards compliance |

Key capabilities:

- Advanced PDF creation with precise layout control
- PDF/A, PDF/UA compliance
- Digital signatures (PAdES)
- Form handling (AcroForms and XFA)
- HTML to PDF conversion (pdfHTML add-on)
- Redaction

**Licensing note**: AGPL requires releasing source code of applications using iText, unless a commercial license is purchased. Evaluate licensing before use in proprietary software.

```java
// PDF creation example
PdfWriter writer = new PdfWriter("output.pdf");
PdfDocument pdf = new PdfDocument(writer);
Document document = new Document(pdf);
document.add(new Paragraph("Hello, World!"));
document.close();
```

### OpenPDF

| Aspect | Details |
| --- | --- |
| Language | Java |
| License | LGPL 2.1 / MPL 2.0 |
| Primary Use | PDF creation (fork of iText 4) |
| Strengths | LGPL-friendly for commercial use, lightweight |

Suitable as a drop-in replacement for legacy iText 4 usage without AGPL concerns.

---

## JavaScript / Node.js Libraries

### pdf.js (Mozilla)

| Aspect | Details |
| --- | --- |
| Language | JavaScript |
| License | Apache License 2.0 |
| Primary Use | PDF rendering and text extraction in browser/Node.js |
| Strengths | Browser-native rendering, widely used, maintained by Mozilla |

Key capabilities:

- Render PDF pages to canvas
- Extract text content with positioning
- Annotation support
- Web worker support for performance

```javascript
// Text extraction in Node.js
const pdfjsLib = require("pdfjs-dist");

async function extractText(pdfPath) {
  const doc = await pdfjsLib.getDocument(pdfPath).promise;
  const page = await doc.getPage(1);
  const textContent = await page.getTextContent();
  const text = textContent.items.map((item) => item.str).join(" ");
  return text;
}
```

### pdf-lib

| Aspect | Details |
| --- | --- |
| Language | JavaScript/TypeScript |
| License | MIT |
| Primary Use | PDF creation and modification |
| Strengths | Pure JavaScript (no native dependencies), works in browser and Node.js |

Key capabilities:

- Create new PDFs from scratch
- Modify existing PDFs (add pages, text, images)
- Fill and read PDF forms
- Embed fonts (including custom fonts)
- Merge and split PDFs

---

## Python Libraries

### pypdf (formerly PyPDF2)

| Aspect | Details |
| --- | --- |
| Language | Python |
| License | BSD |
| Primary Use | PDF reading, merging, splitting, metadata |
| Strengths | Pure Python, no external dependencies, actively maintained |

Key capabilities:

- Text extraction
- PDF merging and splitting
- Page rotation and cropping
- Metadata reading and writing
- Password-protected PDF handling
- Form field reading

```python
from pypdf import PdfReader

reader = PdfReader("input.pdf")
for page in reader.pages:
    text = page.extract_text()
    print(text)
```

### pdfplumber

| Aspect | Details |
| --- | --- |
| Language | Python |
| License | MIT |
| Primary Use | Detailed text and table extraction |
| Strengths | Superior table extraction, visual debugging, positional text data |

Key capabilities:

- Character-level text extraction with position, font, size
- Table detection and extraction (superior to most alternatives)
- Visual debugging (render pages with detected elements highlighted)
- Cropping pages to specific regions before extraction
- Built on pdfminer.six

```python
import pdfplumber

with pdfplumber.open("input.pdf") as pdf:
    page = pdf.pages[0]

    # Extract text
    text = page.extract_text()

    # Extract tables
    tables = page.extract_tables()
    for table in tables:
        for row in table:
            print(row)
```

### ReportLab

| Aspect | Details |
| --- | --- |
| Language | Python |
| License | BSD |
| Primary Use | PDF generation |
| Strengths | Programmatic PDF creation, charts, graphics |

Best for generating reports, invoices, and documents from data — not for reading or parsing PDFs.

---

## Library Selection Guide

| Use Case | Recommended Library |
| --- | --- |
| Simple text extraction (JVM) | Apache PDFBox |
| PDF creation with precise layout (JVM) | iText (check license) or OpenPDF |
| Text extraction in browser | pdf.js |
| PDF manipulation in Node.js | pdf-lib |
| Simple text extraction (Python) | pypdf |
| Table extraction (Python) | pdfplumber |
| PDF generation (Python) | ReportLab |
| OCR on scanned PDFs | Tesseract + preprocessing (see pdf-text-extraction.md) |
| Digital signatures | iText (JVM) |
| PDF/A compliance | iText or PDFBox (preflight) |

## Licensing Summary

| Library | License | Commercial Use |
| --- | --- | --- |
| Apache PDFBox | Apache 2.0 | Free |
| iText 7+ | AGPL 3.0 / Commercial | Requires commercial license for proprietary software |
| OpenPDF | LGPL 2.1 / MPL 2.0 | Free (with LGPL conditions) |
| pdf.js | Apache 2.0 | Free |
| pdf-lib | MIT | Free |
| pypdf | BSD | Free |
| pdfplumber | MIT | Free |
| ReportLab | BSD | Free (open-source edition) |
