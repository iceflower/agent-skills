---
name: pdf-handling
description: >-
  PDF file reading and processing rules.
  Use when analyzing PDF files or extracting content from them.
---

# PDF File Handling Rules

## Conversion Procedure

- When reading PDF files, always follow this procedure:
  1. Convert the required pages to PNG images using `pdftoppm`
  2. Analyze the converted images to extract text
- Never include a PDF file directly in an API request body

## Prerequisite

- `poppler` must be installed
  - macOS: `brew install poppler`
  - openSUSE Tumbleweed: `sudo zypper install poppler-tools`
  - Ubuntu (LTS): `sudo apt install poppler-utils`
  - Windows: `choco install poppler` or `scoop install poppler`

## Page Range Strategy

- Read table of contents pages first to understand structure
- Convert only the pages needed for the current task, not the entire document
- For large PDFs (100+ pages), work in batches of 10-20 pages

## Temporary File Management

- Use `/tmp/` for converted PNG images
- Use descriptive prefixes for output files (e.g., `pdftoppm -png -f 1 -l 5 input.pdf /tmp/project_toc`)
- Clean up temporary PNG files after extraction is complete using `rm /tmp/<prefix>*.png`

## Large PDF Handling

- If the Read tool fails due to file size, always fall back to `pdftoppm`
- Estimate the PDF page offset by comparing displayed page numbers with actual PDF page numbers
- When searching for specific content, use the table of contents to calculate target page numbers rather than scanning sequentially

## Command Reference

### pdftoppm

```bash
# Convert specific page range to PNG
pdftoppm -png -f <first> -l <last> input.pdf /tmp/output_prefix

# Example: convert pages 1-5
pdftoppm -png -f 1 -l 5 input.pdf /tmp/project_toc

# Higher resolution (default 150 DPI, use 300 for small text)
pdftoppm -png -r 300 -f 1 -l 1 input.pdf /tmp/high_res
```

### pdfinfo

```bash
# Check page count, file size, and metadata
pdfinfo input.pdf
```

### pdftotext

```bash
# Extract text from specific pages (preserve layout)
pdftotext -f 1 -l 5 -layout input.pdf /tmp/output.txt

# Extract all text
pdftotext input.pdf /tmp/output.txt
```

## Workflow

### Standard PDF Analysis Procedure

```text
1. Run pdfinfo to check document metadata (page count, size)
2. Convert table of contents pages with pdftoppm to understand structure
3. Selectively convert only the pages needed for the task
4. Analyze images or extract text with pdftotext
5. Clean up temporary files in /tmp/
```

### Page Number Offset Handling

The actual PDF page number and the printed page number in the document may differ.

| Situation                      | Example                           | Resolution                          |
| ------------------------------ | --------------------------------- | ----------------------------------- |
| Cover/preface pages present    | Document "page 1" is PDF page 3  | Apply offset +2                     |
| Roman numeral pages            | i, ii, iii, ...                   | Cross-reference with table of contents |
| Appendix with separate numbers | A-1, A-2, ...                     | Calculate PDF page from table of contents |

## Anti-Patterns

- Converting the entire PDF at once (memory/disk exhaustion on large files)
- Not cleaning up temporary PNG files after extraction
- Converting pages without verifying the page number offset
- Using image conversion when direct text extraction (`pdftotext`) is sufficient

## Related Skills

- `error-handling`: Error handling patterns for PDF parsing failures
- `logging`: Logging PDF processing workflows
- `testing`: Testing strategies for PDF processing logic
