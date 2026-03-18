---
name: pdf-generator
display_name: "PDF Generator"
description: "Generate professional PDF documents from text content, HTML markup, or structured data including invoices, reports, and formatted documents"
category: productivity
icon: file-text
skill_type: sandbox
catalog_type: addon
requirements: "httpx>=0.25\nreportlab>=4.0"
tool_schema:
  name: pdf-generator
  description: "Generate professional PDF documents from text content, HTML markup, or structured data including invoices, reports, and formatted documents"
  parameters:
    type: object
    properties:
      action:
        type: "string"
        description: "Which type of PDF to generate"
        enum: ["text_to_pdf", "invoice_pdf", "report_pdf", "table_pdf"]
      filename:
        type: "string"
        description: "Output filename (without .pdf extension)"
        default: "document"
      title:
        type: "string"
        description: "Document title displayed at the top"
        default: ""
      content:
        type: "string"
        description: "Main text content for text_to_pdf and report_pdf actions"
        default: ""
      author:
        type: "string"
        description: "Author name for the document metadata"
        default: ""
      font_size:
        type: "integer"
        description: "Body text font size in points (8-24)"
        default: 12
      invoice_data:
        type: "object"
        description: "Invoice details for invoice_pdf: {from, to, invoice_number, date, due_date, items: [{description, quantity, unit_price}], notes, currency}"
        default: {}
      table_data:
        type: "object"
        description: "Table data for table_pdf: {headers: [...], rows: [[...], ...], caption}"
        default: {}
      sections:
        type: "array"
        description: "List of report sections for report_pdf: [{heading, body}]"
        default: []
      page_size:
        type: "string"
        description: "Page size: A4 or LETTER"
        enum: ["A4", "LETTER"]
        default: "A4"
    required: [action]
---
# PDF Generator

Generate professional PDF documents directly in the sandbox — no external API needed. Supports plain text documents, invoices, structured reports with sections, and data tables.

## Actions

### text_to_pdf
Convert plain text content into a formatted PDF.

**Example parameters:**