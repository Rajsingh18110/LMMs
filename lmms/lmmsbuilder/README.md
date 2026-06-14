# lmms-builder

**Bootstrapper and Hardware Profiler for the LMMs Engine (Local Machine Model Studio)**

[![Documentation](https://img.shields.io/badge/Documentation-lmms.markanm.com-007A87?style=for-the-badge&logo=read-the-docs&logoColor=white)](https://lmms.markanm.com/)

`lmms-builder` is the official setup, profiling, and installation utility for the LMMs ecosystem. It helps users prepare their systems for running local AI models by detecting hardware capabilities, performing compatibility checks, and installing the optimal LMMs Engine components.

## What It Does

Before running AI models locally, `lmms-builder` analyzes your system and automatically configures the best environment for the LMMs Engine.

It is designed to:

- Detect system hardware and software capabilities.
- Evaluate compatibility for local AI inference.
- Download and install the appropriate LMMs Engine binaries.
- Configure dependencies and runtime environments.
- Diagnose common setup and performance issues.

---

## 📖 Documentation

For detailed guides, CLI command reference, configuration tutorials, and hardware requirements, please visit the official documentation website:

> [!NOTE]
> ### 🌐 Official Documentation
> You can view full documentation and ecosystem resources at:
> **[lmms.markanm.com](https://lmms.markanm.com/)**

---

## Features

### Hardware Profiling

Automatically detects:

- Operating System
- CPU Architecture
- Available RAM
- GPU Model(s)
- GPU VRAM
- CUDA Availability and Version
- Python Environment

### Compatibility Analysis

- Evaluates hardware readiness for local AI workloads.
- Provides compatibility information before installation.
- Helps identify potential bottlenecks.

### Intelligent Installation

- Downloads optimized engine binaries from GitHub Releases.
- Selects the most suitable runtime configuration based on detected hardware.
- Simplifies setup for both CPU-only and GPU-enabled systems.

### Diagnostics & Health Checks

Built-in tools for:

- Dependency verification
- Environment validation
- Configuration troubleshooting
- Performance diagnostics

### Global CLI Access

Installs the LMMs Engine and related tools into your system PATH, allowing commands to be executed from anywhere.

### Protected Distribution

The project uses Cython-based compilation and packaging techniques to help protect proprietary components.

---

## Installation

Install from PyPI:

```bash
pip install lmms-builder
```

---

## Usage

### Automatic Setup

```bash
lmms-builder --autoset
```

Detects hardware, performs compatibility checks, downloads the recommended engine build, and configures the environment.

### Detect Hardware

```bash
lmms-builder detect
```

Displays detailed information about your operating system, CPU, RAM, GPU, CUDA version, and Python environment.

### Check Compatibility

```bash
lmms-builder compatibility
```

Shows compatibility information for local AI inference workloads.

### Run Diagnostics

```bash
lmms-builder doctor
```

Checks for missing dependencies and configuration issues.

### Benchmark System

```bash
lmms-builder benchmark
```

Runs performance tests to identify hardware limitations.

### Install Recommended Components

```bash
lmms-builder install
```

Installs the recommended LMMs Engine components based on your detected hardware profile.

### Install Specific Engine Version

```bash
lmms-builder pull v1.0.0
```

Downloads and installs a specific release.

---

## Workflow

```text
System Scan
     ↓
Hardware Profile
     ↓
Compatibility Analysis
     ↓
Binary Selection
     ↓
Engine Installation
     ↓
Diagnostics & Validation
```

---

## Project Vision

The goal of the LMMs ecosystem is to make local AI deployment simple, accessible, and hardware-aware.

Rather than requiring users to manually select CUDA versions, configure runtimes, and troubleshoot dependencies, `lmms-builder` automates the entire setup process.

---

## Next Step

After setup is complete:

```bash
pip install lmms
```

or launch the installed LMMs Engine using the provided CLI tools.

---

## License

Developed by **MarkanM**.

See the LICENSE file for licensing information.

---

**Part of the LMMs Ecosystem — enabling seamless local, multi-model AI workflows across diverse hardware configurations.**
