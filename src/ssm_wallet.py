import time
import json
import os
import datetime
from typing import Dict, Any, Generator

from quantum_engine import QuantumExecutionEngine
from llm_agent import LocalQwenAgent
from policy_ontology import ExpandablePolicyOntology

HISTORY_FILE = "execution_evidence_log.json"


class SecureSignatureModule:
    def __init__(self):
        self.llm = LocalQwenAgent()
        self.ontology = ExpandablePolicyOntology()
        self.quantum = QuantumExecutionEngine()
        self.max_qkd_distance_km = 100.0

    def save_evidence(self, prompt, thinking_tokens, intent, policy, qrng, quantum_channel_data, qhash, final_status, route):
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt,
            "llm_thinking_tokens": thinking_tokens,
            "parsed_intent": intent,
            "policy_ontology_evaluation": policy,
            "active_ontology_blacklist": self.ontology.get_blacklisted_counterparties(),
            "quantum_nonce": qrng,
            "quantum_channel_physical_state": quantum_channel_data,
            "quantum_hash": qhash,
            "execution_status": final_status,
            "routing_tier": route
        }
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    pass
        history.append(record)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)

    def get_evidence_log(self) -> str:
        if not os.path.exists(HISTORY_FILE):
            return json.dumps({"message": "No execution evidence recorded yet."}, indent=2)
        with open(HISTORY_FILE, "r") as f:
            return json.dumps(json.load(f), indent=2)

    def execute_transaction_stream(self, prompt: str, simulate_eavesdrop=False, simulate_llm_attack=False) -> Generator[str, None, None]:
        log = f"[USER INPUT] {prompt}\n"
        yield log; time.sleep(0.3)

        # 1. Stream raw LLM tokens live (mirrors the Gradio terminal behaviour)
        log += "\n[LLM AGENT] Streaming raw response tokens:\n"
        yield log; time.sleep(0.2)

        intent = {}
        thinking_tokens = ""
        for partial_intent, stream_tokens in self.llm.parse_instruction_to_intent_stream(prompt):
            thinking_tokens = stream_tokens
            if partial_intent:
                intent = partial_intent
            yield log + stream_tokens
        log += thinking_tokens + "\n"

        if simulate_llm_attack:
            intent["amount"] = 999999999
            intent["dest"] = "0xEvil_Contract"

        log += f"\n[LLM AGENT] Unauthenticated Intent Payload:\n{json.dumps(intent, indent=2)}\n"
        yield log; time.sleep(0.5)

        # 2. Evaluate against Expandable Policy Ontology
        policy = self.ontology.evaluate_intent(intent)
        log += f"\n[POLICY ONTOLOGY] Graph Decision:\n{json.dumps(policy, indent=2)}\n"
        yield log; time.sleep(0.5)

        if policy["status"] == "BLOCKED":
            log += f"\n[SECURITY SHIELD] TRANSACTION ABORTED: {policy['reason']}\n"
            self.save_evidence(prompt, thinking_tokens, intent, policy, None, None, None, "BLOCKED", "NONE")
            yield log
            return

        # 3. Request Quantum Random Entropy
        qrng = self.quantum.generate_qrng_nonce()
        log += f"\n[QUANTUM ENGINE] QRNG Entropy Nonce Received: {qrng}\n"
        yield log; time.sleep(0.4)

        tier = policy["required_tier"]
        distance = intent.get("distance_km", 0.0)
        if tier == "Tier2_QKD" and distance > self.max_qkd_distance_km:
            log += f"[SSM ROUTER] Distance ({distance} km) exceeds QKD fiber hardware limits.\n"
            log += "[SSM ROUTER] Downgrading route to Tier 1 Post-Quantum Cryptography (PQC).\n"
            tier = "Tier1_PQC"
            yield log; time.sleep(0.5)

        qhash = self.quantum.compute_quantum_state_hash(intent["intent_id"], qrng)
        quantum_channel_data = None

        if tier == "Tier2_QKD":
            log += "\n[ROUTER] Engaging Tier 2 Quantum Key Distribution (BB84 Protocol)...\n"
            yield log; time.sleep(0.8)

            # Execute actual physical state measurement over fiber channel
            quantum_channel_data = self.quantum.simulate_quantum_channel_transmission(eavesdrop=simulate_eavesdrop)
            log += f"[QKD CHANNEL] Physical State Vector: {quantum_channel_data['state_vector']}\n"
            log += f"[QKD CHANNEL] Measured Fidelity: {quantum_channel_data['fidelity']:.4f} | QBER: {quantum_channel_data['qber']:.2%}\n"
            yield log; time.sleep(0.8)

            if simulate_eavesdrop or quantum_channel_data["intercepted"]:
                log += "\n[QKD ALERT] QUANTUM NO-CLONING THEOREM VIOLATED!\n"
                log += "[QKD ALERT] State vector collapsed in transit. Interception detected.\n"
                log += "[SECURITY SHIELD] KEY DISCARDED. TRANSACTION ABORTED TO PREVENT HNDL.\n"
                self.save_evidence(prompt, thinking_tokens, intent, policy, qrng, quantum_channel_data, None, "ABORTED_EAVESDROP", tier)
                yield log
                return
            else:
                log += "[QKD] Channel measurement nominal. Information-theoretic key distilled.\n"
                yield log; time.sleep(0.6)
        else:
            log += "\n[ROUTER] Engaging Tier 1 Post-Quantum Cryptography (ML-DSA)...\n"
            yield log; time.sleep(0.6)

        log += f"\n[SUCCESS] Transaction executed on-chain. Q-Hash: 0x{qhash}\n"
        self.save_evidence(prompt, thinking_tokens, intent, policy, qrng, quantum_channel_data, qhash, "EXECUTED", tier)
        yield log