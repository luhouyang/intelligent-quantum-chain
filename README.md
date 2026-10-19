# Intelligent-Quantum Chain | IQ-Chain

Submission for 2026 Shenzhen FinTechathon International Track

[DEMO-V1](https://drive.google.com/file/d/1Dw9CHvM61kiFVJfCYaXEq8bdq0XvFU7I/view?usp=sharing)

Test cases can be checked by running [src/headless_demo.py](/src/headless_demo.py) or with UI [src/app.py](/src/app.py)

# Setup

## Linux Setup

### 1. Environment & Dependencies

```bash
python3.12 -m venv iqc
source iqc/bin/activate
python -m pip install --upgrade pip setuptools wheel python-dotenv
pip install networkx gradio qiskit qiskit-ibm-runtime

```

### 2. Ollama & Model

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama run kwangsuklee/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:latest

```

### 3. IBM Quantum API Token

Create `.env` in project root:

```env
IBM_QUANTUM_TOKEN=your_actual_copied_ibm_token_here

```

---

## Windows Setup

### 1. Environment & Dependencies

```powershell
python -m venv iqc
.\iqc\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel python-dotenv
pip install networkx gradio qiskit qiskit-ibm-runtime

```

### 2. Ollama & Model

1. Download and run the installer from [ollama.com/download](https://ollama.com/download)
2. Run in terminal:

```powershell
ollama serve
ollama run kwangsuklee/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:latest

```

### 3. IBM Quantum API Token

Create `.env` in project root:

```env
IBM_QUANTUM_TOKEN=your_actual_copied_ibm_token_here

```
