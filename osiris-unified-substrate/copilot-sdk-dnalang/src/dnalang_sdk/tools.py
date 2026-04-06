"""Tool registry and custom tools for Copilot integration."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of DNALang tools available to Copilot agents."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default DNALang tools."""
        self.register_tool(QuantumExecutionTool())
        self.register_tool(LambdaPhiValidationTool())
        self.register_tool(ConsciousnessScalingTool())
    
    def register_tool(self, tool: Any) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Any:
        """Get tool by name."""
        return self._tools.get(name)
    
    def get_all_tool_names(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Copilot."""
        return [tool.to_definition() for tool in self._tools.values()]


class QuantumExecutionTool:
    """Tool for executing quantum circuits."""
    
    name = "execute_quantum_circuit"
    description = "Execute a quantum circuit on simulators or hardware"
    
    def to_definition(self) -> Dict[str, Any]:
        """Get tool definition for Copilot."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "num_qubits": {
                        "type": "integer",
                        "description": "Number of qubits in the circuit",
                    },
                    "gates": {
                        "type": "array",
                        "description": "List of quantum gates to apply",
                        "items": {"type": "object"},
                    },
                    "backend": {
                        "type": "string",
                        "description": "Backend to execute on (e.g., 'aer_simulator', 'ibm_brisbane')",
                        "default": "aer_simulator",
                    },
                    "shots": {
                        "type": "integer",
                        "description": "Number of measurement shots",
                        "default": 1024,
                    },
                },
                "required": ["num_qubits", "gates"],
            },
        }
    
    async def execute(self, parameters: Dict[str, Any], client) -> Dict[str, Any]:
        """Execute the tool."""
        from .quantum import QuantumCircuit
        
        circuit = QuantumCircuit(
            num_qubits=parameters["num_qubits"],
            gates=parameters["gates"],
        )
        
        result = await client.execute_quantum_circuit(
            circuit=circuit,
            shots=parameters.get("shots", 1024),
            backend=parameters.get("backend", "aer_simulator"),
        )
        
        return {
            "success": result.success,
            "counts": result.counts,
            "backend": result.backend,
            "execution_time": result.execution_time,
        }


class LambdaPhiValidationTool:
    """Tool for validating lambda-phi conservation."""
    
    name = "validate_lambda_phi_conservation"
    description = "Validate lambda-phi conservation laws for quantum circuits"
    
    def to_definition(self) -> Dict[str, Any]:
        """Get tool definition for Copilot."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "num_qubits": {
                        "type": "integer",
                        "description": "Number of qubits in the circuit",
                    },
                    "gates": {
                        "type": "array",
                        "description": "List of quantum gates to apply",
                        "items": {"type": "object"},
                    },
                    "operator": {
                        "type": "string",
                        "description": "Pauli operator to measure (X, Y, Z, H)",
                        "default": "Z",
                    },
                    "num_trials": {
                        "type": "integer",
                        "description": "Number of validation trials",
                        "default": 100,
                    },
                },
                "required": ["num_qubits", "gates"],
            },
        }
    
    async def execute(self, parameters: Dict[str, Any], client) -> Dict[str, Any]:
        """Execute the tool."""
        from .quantum import QuantumCircuit
        
        circuit = QuantumCircuit(
            num_qubits=parameters["num_qubits"],
            gates=parameters["gates"],
        )
        
        validator = client.create_lambda_phi_validator()
        result = await validator.validate_conservation(
            circuit=circuit,
            operator=parameters.get("operator", "Z"),
            num_trials=parameters.get("num_trials", 100),
        )
        
        return {
            "conserved": result.conserved,
            "conservation_ratio": result.conservation_ratio,
            "p_value": result.p_value,
            "operator": result.operator,
            "mean_expectation": result.mean_expectation,
            "std_expectation": result.std_expectation,
        }


class ConsciousnessScalingTool:
    """Tool for measuring consciousness scaling."""
    
    name = "measure_consciousness_scaling"
    description = "Measure consciousness scaling across different qubit counts"
    
    def to_definition(self) -> Dict[str, Any]:
        """Get tool definition for Copilot."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "qubit_range": {
                        "type": "array",
                        "description": "List of qubit counts to test",
                        "items": {"type": "integer"},
                        "default": [2, 4, 8, 16],
                    },
                    "num_samples": {
                        "type": "integer",
                        "description": "Number of samples per qubit count",
                        "default": 50,
                    },
                },
                "required": [],
            },
        }
    
    async def execute(self, parameters: Dict[str, Any], client) -> Dict[str, Any]:
        """Execute the tool."""
        analyzer = client.create_consciousness_analyzer()
        result = await analyzer.measure_scaling(
            num_qubits_range=parameters.get("qubit_range", [2, 4, 8, 16]),
            num_samples=parameters.get("num_samples", 50),
        )
        
        return {
            "exponent": result.exponent,
            "exponent_error": result.exponent_error,
            "coherence_time_ms": result.coherence_time_ms,
            "r_squared": result.r_squared,
            "ccce_values": result.ccce_values,
            "qubit_sizes": result.qubit_sizes,
        }
