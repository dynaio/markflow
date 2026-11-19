# MarkFlow

**Write in Markdown. Preview as PDF. Focus on your work.**

MarkFlow is a native Linux desktop application designed to make writing, editing, and exporting Markdown documents easier.

It combines a distraction-free Markdown editor, project file explorer, and integrated PDF preview in one workspace. Its goal is to provide a practical writing environment for technical documentation, academic reports, and everyday Markdown projects.

> **Status:** Early development — actively being built.

---

## Features

- **Markdown editor** — Write and edit Markdown with syntax highlighting.
- **Integrated PDF preview** — View compiled PDF documents inside the application.
- **Project explorer** — Browse and open files within your project.
- **PDF compilation** — Compile Markdown documents using Pandoc and XeLaTeX.
- **PDF export** — Export documents as PDF.
- **Live compilation** — Automatically trigger compilation when the document changes.
- **Keyboard shortcuts** — Access common editing and file operations quickly.
- **Native Linux application** — Built with Python and PyQt6.

---

## Interface

MarkFlow uses an IDE-inspired layout:

| Panel | Purpose |
|---|---|
| Explorer | Browse project files and directories |
| Editor | Write and edit Markdown documents |
| PDF Preview | View the compiled document |
| Status Bar | Monitor compilation status |

The panels can be resized to suit your workflow.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application development |
| PyQt6 | Desktop graphical interface |
| PyMuPDF | PDF processing support |
| Qt PDF | Embedded PDF viewing |
| Pandoc | Markdown document conversion |
| XeLaTeX | PDF generation |
| WeasyPrint | Planned alternative PDF rendering engine |

---

## Requirements

- Linux (Ubuntu recommended)
- Python 3.10 or newer
- PyQt6
- Pandoc
- XeLaTeX
- A working LaTeX installation

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/dynaio/markflow.git
cd markflow
