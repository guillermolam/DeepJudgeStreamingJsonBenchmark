## Getting Started with DeepJudge Streaming JSON Benchmark

This guide will help you get started with the DeepJudge Streaming JSON Benchmark.
Follow these steps to set up and run the benchmark.

## Prerequisites

- [Python 3.12 or higher](https://www.python.org/)
- [Taskfile](https://taskfile.dev/getting-started/)
- [Git](https://git-scm.com/)
- [Docker](https://www.docker.com/) or [Rancher Desktop](https://rancherdesktop.com/)

## Installation

1. Clone the repository:
    ```bash
    git clone [https://github.com/deepjudge/deepjudge-streaming-json-benchmark.git](https://github.com/deepjudge/deepjudge-streaming-json-benchmark.git)
    cd deepjudge-streaming-json-benchmark
    ```

2. Install [Taskfile](https://taskfile.dev/getting-started/):
    ```bash
    pip install go-task-bin
   winget install Task.Task
   choco install go-task
   scoop install task
   sudo snap install task --classic
   brew install go-task/tap/go-task
   brew install go-task
   nix-env -iA nixpkgs.go-task
    ```

3. Run the Taskfile script:
    ```bash
    task # this will install all dependencies and run the benchmark
   ```
   Other commands:
    - `task setup` to install all dependencies
    - `task ci` to run the benchmark
    - `task lint` to lint the code

## Describe all commands from @Taskfile.yml

Here’s a **clear breakdown** of how to run and use this `Taskfile.yml` with **PowerShell** on Windows.

---

### ✅ Prerequisites

Before running any tasks, ensure:

1. **Go-Task CLI** is installed
   → Install via: `winget install go-task` or [manual install](https://taskfile.dev/installation/)

2. **PowerShell 7+** (already implied via `pwsh`)

3. The following tools must be available:

    * `winget` (usually pre-installed on Windows 11)
    * `python` (added to PATH)
    * `act` [nektos/act](https://github.com/nektos/act) (GitHub Actions runner)
    * `uv` (used for dependency management)
    * `requirements.txt` must be present in the project root

---

### 🚀 How to Run in PowerShell

Each of the commands below must be run in PowerShell from the directory containing your `Taskfile.yml`.

---

## 🧪 1. Full Bootstrap + CI (Default)

```powershell
task
```

This runs the `default` task:

* Verifies `winget`, `task`, `act`
* Creates `.venv`
* Installs `pip`, `uv`, project dependencies
* Configures `.actrc`
* Runs local GitHub Actions via `act`

---

## 🧰 2. Bootstrap Tools Only

```powershell
task bootstrap
```

Runs:

* `task verify:winget`
* `task verify:task`
* `task verify:act`
* `task setup:venv`

---

## ✅ 3. Verify Individual Tool

```powershell
task verify:winget
task verify:task
task verify:act
```

Each of these checks if a specific CLI tool is installed. They run:

* `winget --version`
* `task --version`
* `act --version`

---

## 🐍 4. Set Up Python Virtual Environment

```powershell
task setup:venv
```

Creates `.venv` if it doesn’t exist:

* Uses `python -m venv .venv`

---

## 📦 5. Install Dependencies (via uv)

```powershell
task setup:deps
```

Runs:

* Bootstraps `pip`, `setuptools`, `wheel`, and `uv`
* Verifies `uv.exe` exists in `.venv`
* Installs from `requirements.txt` using `uv pip install`

---

## ⚙️ 6. Configure `.actrc`

```powershell
task configure:act
```

Ensures `.actrc` file contains:

```
--pull never
-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
```

This avoids re-downloading Docker images when running local GitHub Actions with `act`.

---

## 🧪 7. Run Local CI (with act)

```powershell
task ci
```

Executes:

```bash
act -j build-and-test --env RUST_LOG=info
```

---

### 🔄 Summary Table

| Command              | Purpose                                 |
|----------------------|-----------------------------------------|
| `task`               | Full bootstrap + CI run                 |
| `task bootstrap`     | Verify tools + create `.venv`           |
| `task setup:venv`    | Create `.venv` if missing               |
| `task setup:deps`    | Install Python deps using `uv`          |
| `task configure:act` | Setup `.actrc` mapping & flags          |
| `task ci`            | Run local CI workflow with `act`        |
| `task verify:<tool>` | Ensure `winget`, `task`, or `act` exist |

---

