# PDF Text and Table Extraction with OCR

## 1. Text Extraction Methods

### Method Selection

| PDF Type | Method | Tools |
| --- | --- | --- |
| Digital (text-based) PDF | Direct text extraction | pdftotext, pypdf, PDFBox, pdf.js |
| Scanned (image-based) PDF | OCR | Tesseract, Google Cloud Vision, Amazon Textract |
| Mixed (some pages scanned) | Detect and route per page | Combine direct extraction + OCR |

### How to Detect Scanned vs Digital

```python
import pdfplumber

with pdfplumber.open("input.pdf") as pdf:
    page = pdf.pages[0]
    text = page.extract_text()

    if text and len(text.strip()) > 50:
        print("Digital PDF — use direct text extraction")
    else:
        print("Likely scanned — use OCR")
```

```bash
# Quick check with pdftotext
pdftotext -f 1 -l 1 input.pdf - | wc -c
# If character count is very low or zero, the page is likely scanned
```

---

## 2. Table Extraction

### Camelot (Python)

Best for well-structured tables with clear borders or consistent spacing.

| Aspect | Details |
| --- | --- |
| License | MIT |
| Methods | Lattice (bordered tables), Stream (borderless tables) |
| Output | pandas DataFrame, CSV, JSON, HTML, Excel |
| Dependency | Ghostscript, Tkinter (for visual debugging) |

```python
import camelot

# Lattice mode — for tables with visible borders/gridlines
tables = camelot.read_pdf("input.pdf", pages="1-3", flavor="lattice")
print(f"Found {tables.n} tables")

for table in tables:
    print(table.df)               # pandas DataFrame
    print(f"Accuracy: {table.accuracy}")  # Parsing accuracy score

# Stream mode — for tables without borders (uses whitespace patterns)
tables = camelot.read_pdf("input.pdf", pages="1", flavor="stream")

# Export
tables[0].to_csv("table.csv")
tables[0].to_excel("table.xlsx")
tables[0].to_json("table.json")
```

#### Lattice vs Stream

| Mode | Best For | How It Works |
| --- | --- | --- |
| Lattice | Tables with visible cell borders | Detects lines/edges to find cell boundaries |
| Stream | Tables with consistent spacing but no borders | Uses whitespace gaps between text to infer columns |

#### Accuracy Improvement Tips

```python
# Adjust line detection sensitivity for lattice mode
tables = camelot.read_pdf("input.pdf", flavor="lattice",
                          line_scale=40,      # Higher = more sensitive to lines
                          process_background=True)  # Detect colored backgrounds as lines

# Specify table area manually when auto-detection fails
tables = camelot.read_pdf("input.pdf", flavor="stream",
                          table_areas=["72,700,540,300"],  # x1,y1,x2,y2 in PDF points
                          columns=["150,300,450"])          # Column separator x-coordinates
```

### Tabula / tabula-py (Python wrapper for Tabula Java)

| Aspect | Details |
| --- | --- |
| License | MIT |
| Backend | Java (requires JRE) |
| Methods | Lattice, Stream |
| Output | pandas DataFrame, CSV, JSON |

```python
import tabula

# Read all tables from a page
tables = tabula.read_pdf("input.pdf", pages="1", multiple_tables=True)

# Read with specific area
tables = tabula.read_pdf("input.pdf", pages="1",
                         area=[100, 50, 500, 400],  # top, left, bottom, right
                         columns=[150, 300])          # Column boundaries

# Stream mode for borderless tables
tables = tabula.read_pdf("input.pdf", pages="all", stream=True)
```

### Camelot vs Tabula Comparison

| Feature | Camelot | Tabula |
| --- | --- | --- |
| Accuracy (bordered) | High | High |
| Accuracy (borderless) | Good (Stream mode) | Moderate |
| Visual debugging | Yes (plot method) | No |
| Accuracy scoring | Yes (per table) | No |
| Java dependency | No | Yes (JRE required) |
| Performance | Moderate | Fast |
| Active maintenance | Moderate | Active |

### pdfplumber Table Extraction

```python
import pdfplumber

with pdfplumber.open("input.pdf") as pdf:
    page = pdf.pages[0]

    # Extract tables with default settings
    tables = page.extract_tables()

    # Fine-tune table detection
    table_settings = {
        "vertical_strategy": "lines",      # "lines", "lines_strict", "text", "explicit"
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,               # Snap lines within N pixels
        "join_tolerance": 3,               # Join line segments within N pixels
        "min_words_vertical": 3,           # Min words to detect vertical boundary
    }
    tables = page.extract_tables(table_settings)

    # Visual debugging — save annotated image
    im = page.to_image()
    im.debug_tablefinder(table_settings)
    im.save("debug_table.png")
```

---

## 3. OCR with Tesseract

### Installation

```bash
# macOS
brew install tesseract

# openSUSE Tumbleweed
sudo zypper install tesseract-ocr

# Ubuntu
sudo apt install tesseract-ocr

# Install additional language packs
# macOS
brew install tesseract-lang
# Ubuntu
sudo apt install tesseract-ocr-kor tesseract-ocr-jpn
# openSUSE
sudo zypper install tesseract-ocr-traineddata-korean
```

### Basic OCR Workflow

```bash
# 1. Convert PDF to high-res images
pdftoppm -png -r 300 input.pdf /tmp/page

# 2. Run OCR on images
tesseract /tmp/page-01.png /tmp/output-01 -l eng

# 3. OCR with specific output format
tesseract /tmp/page-01.png /tmp/output-01 -l eng pdf      # Searchable PDF
tesseract /tmp/page-01.png /tmp/output-01 -l eng hocr     # HTML with coordinates
tesseract /tmp/page-01.png /tmp/output-01 -l eng tsv      # Tab-separated with positions

# 4. Multi-language OCR
tesseract /tmp/page-01.png /tmp/output-01 -l eng+kor
```

### Python OCR with pytesseract

```python
from PIL import Image
import pytesseract

# Basic OCR
text = pytesseract.image_to_string(Image.open("page.png"), lang="eng")

# OCR with bounding box data
data = pytesseract.image_to_data(Image.open("page.png"),
                                  lang="eng",
                                  output_type=pytesseract.Output.DATAFRAME)

# Filter low-confidence results
high_conf = data[data["conf"] > 60]
```

### Image Preprocessing for Better OCR

Poor image quality is the most common cause of bad OCR results. Preprocess images before OCR:

```python
from PIL import Image, ImageFilter, ImageEnhance
import cv2
import numpy as np

def preprocess_for_ocr(image_path):
    img = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # Binarize (adaptive threshold works better for uneven lighting)
    binary = cv2.adaptiveThreshold(denoised, 255,
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)

    # Deskew (correct rotation)
    coords = np.column_stack(np.where(binary > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = binary.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(binary, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    cv2.imwrite("preprocessed.png", rotated)
    return "preprocessed.png"
```

### OCR Quality Checklist

| Factor | Recommendation |
| --- | --- |
| Resolution | Minimum 300 DPI (use `-r 300` with pdftoppm) |
| Color mode | Grayscale or binary (not color) for text |
| Noise | Apply denoising before OCR |
| Skew | Deskew rotated pages |
| Language | Specify correct language pack (`-l eng+kor`) |
| Confidence | Filter results below confidence threshold (>60%) |
| Font size | Very small text (<8pt) may need upscaling before OCR |

---

## 4. Extraction Strategy Decision Tree

```text
PDF Document
├── Has selectable text?
│   ├── Yes → Direct text extraction
│   │   ├── Simple text → pdftotext, pypdf
│   │   ├── Text with position → pdfplumber, PDFBox
│   │   └── Tables → Camelot, Tabula, pdfplumber
│   └── No (scanned/image) → OCR pipeline
│       ├── Convert to high-res images (pdftoppm -r 300)
│       ├── Preprocess (denoise, deskew, binarize)
│       ├── Run Tesseract OCR
│       └── Post-process (spell check, confidence filtering)
│
├── Contains tables?
│   ├── Tables with borders → Camelot (lattice) or Tabula
│   ├── Tables without borders → Camelot (stream) or pdfplumber
│   └── Complex nested tables → Manual area specification + pdfplumber
│
└── Mixed content (text + scanned pages)?
    └── Detect per page → route to direct extraction or OCR
```
