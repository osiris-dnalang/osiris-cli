#!/usr/bin/env python3
"""
dna_ledger.py - DNA-Lang Immutable Ledger
Cryptographic lineage tracking for quantum organisms
"""

import hashlib
import json
import sqlite3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from .dna_ir import QuantumCircuitIR
from .dna_evolve import FitnessMetrics, EvolutionResult
from .dna_runtime import ExecutionResult

# ==========================================
# LEDGER ENTRY STRUCTURES
# ==========================================

@dataclass
class LineageEntry:
    """Single entry in the organism lineage"""
    
    # Identity
    lineage_hash: str
    organism_name: str
    generation: int
    
    # Ancestry
    parent_hash: Optional[str] = None
    ancestor_hashes: List[str] = field(default_factory=list)
    
    # Circuit specification
    gate_count: int = 0
    circuit_depth: int = 0
    qubit_count: int = 0
    qasm_hash: str = ""
    
    # Fitness metrics
    lambda_coherence: float = 0.0
    gamma_decoherence: float = 0.0
    phi_integrated_info: float = 0.0
    w2_distance: float = 0.0
    fitness_score: float = 0.0
    
    # Execution data
    execution_backend: Optional[str] = None
    execution_timestamp: Optional[str] = None
    execution_fidelity: float = 0.0
    measurement_counts: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    created_at: str = ""
    verified: bool = False
    verification_hash: str = ""
    
    def compute_verification_hash(self) -> str:
        """Compute cryptographic verification hash"""
        data = (
            f"{self.lineage_hash}:{self.organism_name}:{self.generation}:"
            f"{self.parent_hash}:{self.gate_count}:{self.circuit_depth}:"
            f"{self.fitness_score}:{self.created_at}"
        )
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class EvolutionLineage:
    """Complete evolutionary lineage of an organism family"""
    
    root_hash: str
    root_organism: str
    current_generation: int
    
    # Lineage tree
    entries: List[LineageEntry] = field(default_factory=list)
    
    # Statistics
    total_organisms: int = 0
    avg_fitness: float = 0.0
    best_fitness: float = 0.0
    best_organism_hash: str = ""
    
    # Milestones
    speciation_events: List[Dict[str, Any]] = field(default_factory=list)
    fitness_breakthroughs: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_entry(self, entry: LineageEntry):
        """Add entry to lineage"""
        self.entries.append(entry)
        self.total_organisms += 1
        self.current_generation = max(self.current_generation, entry.generation)
        
        # Update statistics
        fitnesses = [e.fitness_score for e in self.entries]
        self.avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        
        if entry.fitness_score > self.best_fitness:
            self.best_fitness = entry.fitness_score
            self.best_organism_hash = entry.lineage_hash
            
            # Record breakthrough
            self.fitness_breakthroughs.append({
                'generation': entry.generation,
                'fitness': entry.fitness_score,
                'lineage_hash': entry.lineage_hash,
                'timestamp': entry.created_at
            })

# ==========================================
# LEDGER DATABASE
# ==========================================

class QuantumLedger:
    """Immutable ledger for quantum organism lineages"""
    
    def __init__(self, db_path: str = "quantum_ledger.db"):
        self.db_path = Path(db_path)
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        
        # Lineage entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lineage_entries (
                lineage_hash TEXT PRIMARY KEY,
                organism_name TEXT NOT NULL,
                generation INTEGER NOT NULL,
                parent_hash TEXT,
                ancestor_hashes TEXT,
                gate_count INTEGER,
                circuit_depth INTEGER,
                qubit_count INTEGER,
                qasm_hash TEXT,
                lambda_coherence REAL,
                gamma_decoherence REAL,
                phi_integrated_info REAL,
                w2_distance REAL,
                fitness_score REAL,
                execution_backend TEXT,
                execution_timestamp TEXT,
                execution_fidelity REAL,
                measurement_counts TEXT,
                created_at TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                verification_hash TEXT
            )
        """)
        
        # Evolution lineages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_lineages (
                root_hash TEXT PRIMARY KEY,
                root_organism TEXT NOT NULL,
                current_generation INTEGER,
                total_organisms INTEGER,
                avg_fitness REAL,
                best_fitness REAL,
                best_organism_hash TEXT,
                speciation_events TEXT,
                fitness_breakthroughs TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Execution log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lineage_hash TEXT NOT NULL,
                job_id TEXT,
                backend TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_time REAL,
                timestamp TEXT NOT NULL,
                counts TEXT,
                fidelity REAL,
                error TEXT,
                FOREIGN KEY (lineage_hash) REFERENCES lineage_entries(lineage_hash)
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_organism_name ON lineage_entries(organism_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_generation ON lineage_entries(generation)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fitness ON lineage_entries(fitness_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent ON lineage_entries(parent_hash)")
        
        self.conn.commit()
    
    def record_organism(self, 
                       circuit: QuantumCircuitIR,
                       fitness: Optional[FitnessMetrics] = None,
                       execution: Optional[ExecutionResult] = None) -> LineageEntry:
        """
        Record organism in ledger
        
        Args:
            circuit: Quantum circuit to record
            fitness: Fitness metrics
            execution: Execution result
            
        Returns:
            Lineage entry
        """
        # Create lineage entry
        entry = LineageEntry(
            lineage_hash=circuit.lineage_hash,
            organism_name=circuit.name,
            generation=circuit.generation,
            parent_hash=circuit.parent_hash,
            gate_count=circuit.gate_count,
            circuit_depth=circuit.depth,
            qubit_count=circuit.qubit_count,
            qasm_hash=self._compute_qasm_hash(circuit),
            lambda_coherence=circuit.lambda_coherence,
            gamma_decoherence=circuit.gamma_decoherence,
            phi_integrated_info=circuit.phi_integrated_info,
            w2_distance=circuit.w2_distance,
            created_at=datetime.now().isoformat()
        )
        
        # Add fitness if provided
        if fitness:
            entry.fitness_score = fitness.fitness
        
        # Add execution data if provided
        if execution:
            entry.execution_backend = execution.backend
            entry.execution_timestamp = execution.timestamp
            entry.execution_fidelity = execution.fidelity
            entry.measurement_counts = execution.counts
        
        # Compute verification
        entry.verification_hash = entry.compute_verification_hash()
        entry.verified = True
        
        # Store in database
        self._insert_lineage_entry(entry)
        
        # Update evolution lineage
        self._update_evolution_lineage(entry)
        
        return entry
    
    def _compute_qasm_hash(self, circuit: QuantumCircuitIR) -> str:
        """Compute hash of QASM representation"""
        qasm = circuit.to_qasm()
        return hashlib.sha256(qasm.encode()).hexdigest()[:16]
    
    def _insert_lineage_entry(self, entry: LineageEntry):
        """Insert lineage entry into database"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO lineage_entries VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            entry.lineage_hash,
            entry.organism_name,
            entry.generation,
            entry.parent_hash,
            json.dumps(entry.ancestor_hashes),
            entry.gate_count,
            entry.circuit_depth,
            entry.qubit_count,
            entry.qasm_hash,
            entry.lambda_coherence,
            entry.gamma_decoherence,
            entry.phi_integrated_info,
            entry.w2_distance,
            entry.fitness_score,
            entry.execution_backend,
            entry.execution_timestamp,
            entry.execution_fidelity,
            json.dumps(entry.measurement_counts),
            entry.created_at,
            1 if entry.verified else 0,
            entry.verification_hash
        ))
        
        self.conn.commit()
    
    def _update_evolution_lineage(self, entry: LineageEntry):
        """Update or create evolution lineage"""
        cursor = self.conn.cursor()
        
        # Find root hash (organism with no parent)
        root_hash = self._find_root_hash(entry)
        
        # Check if lineage exists
        cursor.execute("SELECT * FROM evolution_lineages WHERE root_hash = ?", (root_hash,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing lineage
            self._increment_lineage_stats(root_hash, entry)
        else:
            # Create new lineage
            lineage = EvolutionLineage(
                root_hash=root_hash,
                root_organism=entry.organism_name,
                current_generation=entry.generation,
                total_organisms=1,
                avg_fitness=entry.fitness_score,
                best_fitness=entry.fitness_score,
                best_organism_hash=entry.lineage_hash
            )
            self._insert_evolution_lineage(lineage)
    
    def _find_root_hash(self, entry: LineageEntry) -> str:
        """Find root hash of lineage"""
        if not entry.parent_hash:
            return entry.lineage_hash
        
        # Traverse back to root
        cursor = self.conn.cursor()
        current_hash = entry.parent_hash
        
        while True:
            cursor.execute("SELECT parent_hash FROM lineage_entries WHERE lineage_hash = ?", 
                          (current_hash,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                return current_hash
            
            current_hash = result[0]
    
    def _increment_lineage_stats(self, root_hash: str, entry: LineageEntry):
        """Increment statistics for evolution lineage"""
        cursor = self.conn.cursor()
        
        # Get current lineage
        cursor.execute("SELECT * FROM evolution_lineages WHERE root_hash = ?", (root_hash,))
        row = cursor.fetchone()
        
        if not row:
            return
        
        # Update statistics
        total_organisms = row[3] + 1
        avg_fitness = (row[4] * row[3] + entry.fitness_score) / total_organisms
        best_fitness = max(row[5], entry.fitness_score)
        best_organism_hash = entry.lineage_hash if entry.fitness_score > row[5] else row[6]
        current_generation = max(row[2], entry.generation)
        
        # Load and update breakthroughs
        breakthroughs = json.loads(row[8]) if row[8] else []
        if entry.fitness_score > row[5]:
            breakthroughs.append({
                'generation': entry.generation,
                'fitness': entry.fitness_score,
                'lineage_hash': entry.lineage_hash,
                'timestamp': entry.created_at
            })
        
        cursor.execute("""
            UPDATE evolution_lineages SET
                current_generation = ?,
                total_organisms = ?,
                avg_fitness = ?,
                best_fitness = ?,
                best_organism_hash = ?,
                fitness_breakthroughs = ?,
                updated_at = ?
            WHERE root_hash = ?
        """, (
            current_generation,
            total_organisms,
            avg_fitness,
            best_fitness,
            best_organism_hash,
            json.dumps(breakthroughs),
            datetime.now().isoformat(),
            root_hash
        ))
        
        self.conn.commit()
    
    def _insert_evolution_lineage(self, lineage: EvolutionLineage):
        """Insert evolution lineage"""
        cursor = self.conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO evolution_lineages VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            lineage.root_hash,
            lineage.root_organism,
            lineage.current_generation,
            lineage.total_organisms,
            lineage.avg_fitness,
            lineage.best_fitness,
            lineage.best_organism_hash,
            json.dumps(lineage.speciation_events),
            json.dumps(lineage.fitness_breakthroughs),
            now,
            now
        ))
        
        self.conn.commit()
    
    def record_execution(self, 
                        lineage_hash: str,
                        execution: ExecutionResult):
        """Record execution in log"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO execution_log (
                lineage_hash, job_id, backend, status, execution_time,
                timestamp, counts, fidelity, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lineage_hash,
            execution.job_id,
            execution.backend,
            execution.status,
            execution.execution_time,
            execution.timestamp,
            json.dumps(execution.counts),
            execution.fidelity,
            execution.error
        ))
        
        self.conn.commit()
    
    def get_lineage(self, lineage_hash: str) -> Optional[LineageEntry]:
        """Get lineage entry by hash"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM lineage_entries WHERE lineage_hash = ?", (lineage_hash,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_lineage_entry(row)
    
    def get_evolution_lineage(self, root_hash: str) -> Optional[EvolutionLineage]:
        """Get complete evolution lineage"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM evolution_lineages WHERE root_hash = ?", (root_hash,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Get all entries in this lineage
        cursor.execute("""
            SELECT * FROM lineage_entries 
            WHERE lineage_hash = ? OR parent_hash IN (
                SELECT lineage_hash FROM lineage_entries WHERE lineage_hash = ?
                UNION
                SELECT lineage_hash FROM lineage_entries WHERE parent_hash = ?
            )
            ORDER BY generation
        """, (root_hash, root_hash, root_hash))
        
        entries = [self._row_to_lineage_entry(r) for r in cursor.fetchall()]
        
        return EvolutionLineage(
            root_hash=row[0],
            root_organism=row[1],
            current_generation=row[2],
            total_organisms=row[3],
            avg_fitness=row[4],
            best_fitness=row[5],
            best_organism_hash=row[6],
            speciation_events=json.loads(row[7]) if row[7] else [],
            fitness_breakthroughs=json.loads(row[8]) if row[8] else [],
            entries=entries
        )
    
    def get_ancestors(self, lineage_hash: str) -> List[LineageEntry]:
        """Get all ancestors of organism"""
        ancestors = []
        cursor = self.conn.cursor()
        current_hash = lineage_hash
        
        while current_hash:
            cursor.execute("SELECT * FROM lineage_entries WHERE lineage_hash = ?", 
                          (current_hash,))
            row = cursor.fetchone()
            
            if not row:
                break
            
            entry = self._row_to_lineage_entry(row)
            ancestors.append(entry)
            current_hash = entry.parent_hash
        
        return ancestors
    
    def get_best_organisms(self, limit: int = 10) -> List[LineageEntry]:
        """Get best organisms by fitness"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM lineage_entries 
            ORDER BY fitness_score DESC 
            LIMIT ?
        """, (limit,))
        
        return [self._row_to_lineage_entry(row) for row in cursor.fetchall()]
    
    def _row_to_lineage_entry(self, row) -> LineageEntry:
        """Convert database row to LineageEntry"""
        return LineageEntry(
            lineage_hash=row[0],
            organism_name=row[1],
            generation=row[2],
            parent_hash=row[3],
            ancestor_hashes=json.loads(row[4]) if row[4] else [],
            gate_count=row[5],
            circuit_depth=row[6],
            qubit_count=row[7],
            qasm_hash=row[8],
            lambda_coherence=row[9],
            gamma_decoherence=row[10],
            phi_integrated_info=row[11],
            w2_distance=row[12],
            fitness_score=row[13],
            execution_backend=row[14],
            execution_timestamp=row[15],
            execution_fidelity=row[16],
            measurement_counts=json.loads(row[17]) if row[17] else {},
            created_at=row[18],
            verified=bool(row[19]),
            verification_hash=row[20]
        )
    
    def export_lineage(self, root_hash: str, output_path: str):
        """Export lineage to JSON"""
        lineage = self.get_evolution_lineage(root_hash)
        
        if not lineage:
            raise ValueError(f"Lineage {root_hash} not found")
        
        data = {
            'root_hash': lineage.root_hash,
            'root_organism': lineage.root_organism,
            'current_generation': lineage.current_generation,
            'statistics': {
                'total_organisms': lineage.total_organisms,
                'avg_fitness': lineage.avg_fitness,
                'best_fitness': lineage.best_fitness,
                'best_organism_hash': lineage.best_organism_hash
            },
            'milestones': {
                'speciation_events': lineage.speciation_events,
                'fitness_breakthroughs': lineage.fitness_breakthroughs
            },
            'entries': [entry.to_dict() for entry in lineage.entries]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

# ==========================================
# MAIN INTERFACE
# ==========================================

if __name__ == "__main__":
    from dna_parser import parse_dna_lang
    from dna_ir import compile_to_ir
    from dna_evolve import evolve_organism
    from dna_runtime import execute_circuit
    
    # Test ledger
    test_source = """
organism ledger_test {
    quantum_state {
        helix(q[0]);
        bond(q[0], q[1]);
        measure(q[0]);
        measure(q[1]);
    }
    
    fitness = phi;
}
"""
    
    print("=== Quantum Ledger Test ===")
    
    # Initialize ledger
    ledger = QuantumLedger("test_ledger.db")
    
    # Parse and compile
    organisms = parse_dna_lang(test_source)
    circuit = compile_to_ir(organisms[0])
    
    # Execute
    execution = execute_circuit(circuit, use_simulator=True)
    
    # Record in ledger
    entry = ledger.record_organism(circuit, execution=execution)
    
    print(f"\nRecorded organism: {entry.organism_name}")
    print(f"  Lineage hash: {entry.lineage_hash}")
    print(f"  Generation: {entry.generation}")
    print(f"  Fitness: {entry.fitness_score:.4f}")
    print(f"  Verified: {entry.verified}")
    
    # Evolve and record lineage
    print("\nEvolving organism...")
    evolution = evolve_organism(circuit, generations=5, population_size=4)
    
    for i in range(min(3, len(evolution.population_history[-1]))):
        evolved_circuit = evolution.population_history[-1][i]
        evolved_execution = execute_circuit(evolved_circuit, use_simulator=True)
        ledger.record_organism(evolved_circuit, execution=evolved_execution)
    
    # Get evolution lineage
    lineage = ledger.get_evolution_lineage(entry.lineage_hash)
    
    print(f"\nEvolution Lineage:")
    print(f"  Root: {lineage.root_organism}")
    print(f"  Generations: {lineage.current_generation}")
    print(f"  Total organisms: {lineage.total_organisms}")
    print(f"  Average fitness: {lineage.avg_fitness:.4f}")
    print(f"  Best fitness: {lineage.best_fitness:.4f}")
    
    # Export lineage
    ledger.export_lineage(entry.lineage_hash, "test_lineage.json")
    print(f"\nLineage exported to test_lineage.json")
    
    ledger.close()
