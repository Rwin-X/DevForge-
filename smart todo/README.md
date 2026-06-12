# Smart Todo

A minimal, modern desktop to-do app built with Python and CustomTkinter.
Clean dark UI, local JSON storage, zero dependencies beyond the standard library and one UI package.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-7C6EF7?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## Features

- **Add tasks** — type and press Enter or click Add
- **Complete tasks** — checkbox toggles done state with visual feedback
- **Delete tasks** — remove any task with one click
- **Progress bar** — thin accent bar shows completion at a glance
- **Auto-save** — every change is written to `tasks.json` instantly
- **Auto-load** — tasks are restored from disk on every launch

---

## Project Structure

```
SmartTodo/
├── main.py        # Application source (~160 lines)
├── tasks.json     # Local task storage (auto-managed)
└── README.md
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/smart-todo.git
cd smart-todo
```

### 2. Install the dependency

```bash
pip install customtkinter
```

### 3. Run

```bash
python main.py
```

---

## Requirements

| Package        | Version  |
|----------------|----------|
| Python         | 3.10+    |
| customtkinter  | 5.x      |

No database, no accounts, no cloud — just a file on your disk.

---

---

## License

MIT — free to use and modify.
