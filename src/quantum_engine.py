import os
import hashlib
import random
from typing import Dict, Any
from dotenv import load_dotenv

# Split imports: local Qiskit sim is independent of IBM cloud runtime
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import Statevector, state_fidelity
    HAS_QISKIT = True
    QISKIT_IMPORT_ERROR = None
except ImportError as e:
    HAS_QISKIT = False
    QISKIT_IMPORT_ERROR = e

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    HAS_IBM_RUNTIME = True
    IBM_RUNTIME_IMPORT_ERROR = None
except ImportError as e:
    HAS_IBM_RUNTIME = False
    IBM_RUNTIME_IMPORT_ERROR = e

TOKEN_ENV_NAMES = ("IBM_QUANTUM_TOKEN", "QISKIT_IBM_TOKEN", "IBM_CLOUD_API_KEY")
INSTANCE_ENV_NAMES = ("IBM_QUANTUM_INSTANCE", "QISKIT_IBM_INSTANCE", "IBM_CLOUD_CRN")

# qiskit-ibm-runtime >= 1.0 removed "ibm_quantum"; try newest first, oldest last.
CHANNEL_CANDIDATES = ("ibm_quantum_platform", "ibm_cloud", "ibm_quantum")


class QuantumExecutionEngine:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        load_dotenv()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(base_dir, ".env"))
        load_dotenv(os.path.join(base_dir, "..", ".env"))

        self.ibm_token = next((os.getenv(n) for n in TOKEN_ENV_NAMES if os.getenv(n)), None)
        self.ibm_instance = next((os.getenv(n) for n in INSTANCE_ENV_NAMES if os.getenv(n)), None)
        self.ibm_service = None
        self.service_error = None
        self.active_channel = None
        self.last_cloud_error = None

        if not HAS_IBM_RUNTIME:
            self.service_error = f"qiskit-ibm-runtime import failed: {IBM_RUNTIME_IMPORT_ERROR}"
        elif not self.ibm_token:
            self.service_error = f"No API token found in env vars {TOKEN_ENV_NAMES}"
        else:
            self.ibm_service, self.service_error, self.active_channel = self._connect()

        if self.verbose and self.service_error:
            print(f"[QUANTUM ENGINE] IBM cloud unavailable: {self.service_error}")

    def _connect(self):
        """Negotiate a working channel across qiskit-ibm-runtime versions."""
        errors = []
        for channel in CHANNEL_CANDIDATES:
            try:
                # Added instance="auto" to silence the open-instance warning
                kwargs = {"channel": channel, "token": self.ibm_token, "instance": "auto"}
                if channel == "ibm_cloud" and self.ibm_instance:
                    kwargs["instance"] = self.ibm_instance
                service = QiskitRuntimeService(**kwargs)
                return service, None, channel
            except Exception as e:
                errors.append(f"[{channel}] {type(e).__name__}: {e}")
        return None, " | ".join(errors), None

    def diagnose(self) -> str:
        lines = [
            f"HAS_QISKIT (local sim):    {HAS_QISKIT}  {QISKIT_IMPORT_ERROR or ''}",
            f"HAS_IBM_RUNTIME (cloud):   {HAS_IBM_RUNTIME}  {IBM_RUNTIME_IMPORT_ERROR or ''}",
            f"Token loaded:              {bool(self.ibm_token)}",
            f"Service connected:         {self.ibm_service is not None}",
            f"Active channel:            {self.active_channel or 'none'}",
            f"Service error:             {self.service_error or 'none'}",
            f"Last cloud sampling error: {self.last_cloud_error or 'none'}",
        ]
        if self.ibm_service:
            try:
                lines.append(f"Operational QPUs: {[b.name for b in self.ibm_service.backends(operational=True, simulator=False)][:6]}")
            except Exception as e:
                lines.append(f"Backend listing error: {type(e).__name__}: {e}")
        return "\n".join(lines)

    def simulate_quantum_channel_transmission(self, num_qubits: int = 4, eavesdrop: bool = False) -> Dict[str, Any]:
        """
        Simulates physical quantum state transmission over fiber.
        If eavesdrop=True, Eve performs a non-unitary measurement in transit,
        collapsing the quantum superposition and degrading state fidelity.
        """
        if not HAS_QISKIT:
            # Mathematical physical fallback
            if eavesdrop:
                return {"fidelity": 0.50, "qber": 0.25, "intercepted": True, "state_vector": "|01> (COLLAPSED BY EVE)"}
            return {"fidelity": 1.00, "qber": 0.00, "intercepted": False, "state_vector": "(|00> + |11>)/√2 (PRISTINE ENTANGLEMENT)"}

        # 1. Prepare pristine entangled Bell state (Alice)
        qc = QuantumCircuit(num_qubits)
        qc.h(0)
        for i in range(1, num_qubits):
            qc.cx(0, i)
        pristine_state = Statevector.from_instruction(qc)

        if eavesdrop:
            # Eve performs an unauthorized measurement on the quantum channel
            eavesdrop_circuit = qc.copy()
            eavesdrop_circuit.measure_all()
            # Collapse the state vector via measurement projection
            intercepted_state = pristine_state.measure()[1]
            fidelity = float(state_fidelity(pristine_state, intercepted_state))
            qber = round(1.0 - fidelity, 4)
            return {
                "fidelity": fidelity,
                "qber": qber,
                "intercepted": True,
                "state_vector": str(intercepted_state)
            }
        else:
            return {
                "fidelity": 1.00,
                "qber": 0.00,
                "intercepted": False,
                "state_vector": str(pristine_state)
            }

    def generate_qrng_nonce(self, num_qubits: int = 8, strict_cloud: bool = False) -> str:
        # GATE 1: real IBM hardware sampling
        if self.ibm_service is not None:
            try:
                qc = QuantumCircuit(num_qubits)
                for i in range(num_qubits):
                    qc.h(i)
                qc.measure_all()
                
                try:
                    backend = self.ibm_service.least_busy(operational=True, simulator=False)
                except Exception:
                    backend = self.ibm_service.least_busy(operational=True)
                
                # Transpile the circuit to the target backend's ISA (Instruction Set Architecture)
                # This is strictly required by SamplerV2 since March 2024.
                isa_qc = transpile(qc, backend)
                
                sampler = SamplerV2(backend)
                job = sampler.run([isa_qc], shots=1)
                pub_result = job.result()[0]
                
                # Extract the bitstring from the 'meas' classical register created by measure_all()
                bitstring = list(pub_result.data.meas.get_counts().keys())[0]
                return f"QRNG-IBM-CLOUD-{backend.name}-{bitstring}"   # backend name proves origin
                
            except Exception as e:
                self.last_cloud_error = f"{type(e).__name__}: {e}"
                if self.verbose:
                    print(f"[QUANTUM ENGINE] IBM cloud sampling failed: {self.last_cloud_error} -> local sim fallback")
                if strict_cloud:
                    raise RuntimeError(f"IBM cloud QRNG failed: {self.last_cloud_error}") from e

        # GATE 2: local Qiskit statevector sampling
        if HAS_QISKIT:
            qc = QuantumCircuit(num_qubits)
            for i in range(num_qubits):
                qc.h(i)
            state = Statevector.from_instruction(qc)
            measured = random.choices(range(2 ** num_qubits), weights=state.probabilities())[0]
            return f"QRNG-QISKIT-SIM-{bin(measured)[2:].zfill(num_qubits)}"

        # GATE 3: classical fallback
        raw_bits = "".join([str(random.choice([0, 1])) for _ in range(num_qubits)])
        return f"QRNG-CLASSICAL-FALLBACK-{raw_bits}"

    def compute_quantum_state_hash(self, intent_id: str, qrng_nonce: str) -> str:
        data_str = f"{intent_id}_{qrng_nonce}"
        numeric_hash = int(hashlib.sha256(data_str.encode()).hexdigest(), 16)
        theta = (numeric_hash % 360) * (3.14159 / 180.0)
        phi = ((numeric_hash >> 16) % 360) * (3.14159 / 180.0)

        probabilities = {}
        if HAS_QISKIT:
            qc = QuantumCircuit(2)
            qc.rx(theta, 0)
            qc.ry(phi, 1)
            qc.cx(0, 1)
            state = Statevector.from_instruction(qc)
            probs = state.probabilities()
            probabilities = {"|00>": float(probs[0]), "|01>": float(probs[1]), "|10>": float(probs[2]), "|11>": float(probs[3])}
        else:
            probabilities = {"|00>": 0.25, "|01>": 0.25, "|10>": 0.25, "|11>": 0.25}

        return hashlib.sha3_256(f"{data_str}_{probabilities}".encode()).hexdigest()


# if __name__ == "__main__":
#     print(QuantumExecutionEngine(verbose=False).diagnose())