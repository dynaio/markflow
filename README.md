# MarkFlow

**Write in Markdown. Preview as PDF. Focus on your work.**

MarkFlow is a native Linux desktop Markdown editor designed for technical documentation, academic reports, and everyday writing.

It combines a Markdown editor, project explorer, and integrated PDF preview in one workspace.

> **Status:** Early development — actively being built.

## Features

- Markdown editing with syntax highlighting.
- Integrated PDF preview.
- Project file explorer.
- PDF compilation and export.
- Live compilation.
- Keyboard shortcuts.
- Resizable workspace panels.
- Native Linux desktop interface.

## Interface

| Panel | Purpose |
|---|---|
| Explorer | Browse project files and directories |
| Editor | Write and edit Markdown documents |
| PDF Preview | View compiled documents |
| Status Bar | Monitor application status |

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application development |
| PyQt6 | Desktop graphical interface |
| Pygments | Syntax highlighting |
| Pandoc | Markdown conversion |
| XeLaTeX | PDF generation |

## Requirements

- Linux (Ubuntu recommended).
- Python 3.10 or newer.
- pip and Python virtual environment support.
- Pandoc and XeLaTeX for PDF compilation.

## Installation

### 1. Install system dependencies

On Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip pandoc texlive-xetex
