# ArborMind: A Self-Evolving Attention-Based Framework for Autonomous Code Generation

**Version:** 1.0  
**Authors:** GenCode AI Research Team  
**Date:** December 2024  
**System:** GenCode Studio FAST v2 Orchestrator

---

## Abstract

We present **ArborMind (AM)**, a novel framework for autonomous code generation that combines transformer-style attention mechanisms with self-evolving intelligence. Unlike traditional rule-based orchestration systems, ArborMind treats every decision point as an attention-weighted synthesis problem, enabling the system to blend multiple strategies, learn from outcomes, and creatively escape local minima during complex software generation tasks.

ArborMind introduces three core operators—**Combinational (C-AM)**, **Exploratory (E-AM)**, and **Transformational (T-AM)**—that form an escalation ladder from precise routing to creative constraint mutation. The framework demonstrates significant improvements in first-attempt success rates, reduced token consumption, and the ability to recover from previously unrecoverable failure states.

**Keywords:** Attention Mechanism, Self-Evolving Systems, Code Generation, Multi-Agent Orchestration, V≠K Architecture, Transformer Applications

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Minimal Working Example](#3-minimal-working-example)
4. [API Reference](#4-api-reference)
5. [State Machine Diagram](#5-state-machine-diagram)
6. [Data Models & Internal Representations](#6-data-models--internal-representations)
7. [Computational Complexity Analysis](#7-computational-complexity-analysis)
8. [Example Reasoning Cycle Breakdown](#8-example-reasoning-cycle-breakdown)
9. [Background and Related Work](#9-background-and-related-work)
10. [The ArborMind Architecture](#10-the-arbormind-architecture)
11. [Mathematical Foundation: V≠K Attention](#11-mathematical-foundation-vk-attention)
12. [The Three AM Operators](#12-the-three-am-operators)
13. [Self-Evolution Layer](#13-self-evolution-layer)
14. [System Integration](#14-system-integration)
15. [Implementation Details](#15-implementation-details)
16. [Implementation Notes & Best Practices](#16-implementation-notes--best-practices)
17. [Versioning & Extensibility](#17-versioning--extensibility)
18. [Experimental Results](#18-experimental-results)
19. [Discussion](#19-discussion)
20. [Future Work](#20-future-work)
21. [Conclusion](#21-conclusion)
22. [References](#22-references)
23. [Appendix](#appendix)

---

## 1. Introduction

### 1.1 What is ArborMind?

**ArborMind (AM)** is a self-evolving, attention-based framework for intelligent decision-making in autonomous code generation systems. It is the core orchestration intelligence layer powering GenCode Studio's FAST v2 workflow engine.

In simple terms, ArborMind:
- **Routes queries** to the best-matching strategies using transformer-style attention
- **Blends configurations** when queries span multiple domains
- **Learns from outcomes** to improve future decisions without retraining
- **Escalates creatively** when standard approaches fail

### 1.2 Why ArborMind Exists

Traditional code generation orchestrators suffer from:

| Problem | Impact |
|:--------|:-------|
| **Brittle rule-based routing** | Fails on edge cases, requires constant maintenance |
| **Single-label classification** | Cannot handle queries that span multiple domains |
| **Static configurations** | One-size-fits-all approaches waste tokens and miss nuances |
| **No learning loop** | Same mistakes repeated across projects |
| **No escape from failures** | Gets stuck on novel error patterns |

ArborMind solves these by treating every decision as an **attention-weighted synthesis problem** with self-evolution capabilities.

### 1.3 What Problems ArborMind Solves

1. **Tool Selection**: Dynamically select which tools to inject into agent context based on current task
2. **Context Optimization**: Choose which files to include in LLM context windows
3. **Error Recovery**: Route error patterns to appropriate repair strategies
4. **Project Classification**: Semantic archetype and UI vibe detection
5. **Supervision Policy**: Decide when to retry, heal, or abort failed operations
6. **Multi-Domain Queries**: Handle requests that span multiple project archetypes

### 1.4 Contributions

1. **V≠K Attention Architecture**: Values are arbitrary JSON configs, not embeddings
2. **Three-Operator Framework**: C-AM, E-AM, T-AM escalation ladder
3. **Self-Evolution Mechanism**: EMA-based V-vector learning without retraining
4. **Production Integration**: Battle-tested in FAST v2 code generation engine

---

## 2. Architecture Overview

### 2.1 Component Hierarchy

```
ArborMind Architecture
═══════════════════════════════════════════════════════════════════════════════

                           ┌─────────────────────────┐
                           │      USER REQUEST       │
                           │   "Build a dashboard"   │
                           └───────────┬─────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ARBORMIND CORE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                        TREE ENGINE                                 │    │
│   │                                                                    │    │
│   │    Root Problem ──┬── Branch A (Architecture)                     │    │
│   │                   ├── Branch B (Frontend)                         │    │
│   │                   └── Branch C (Backend)                          │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼                                          │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                     ATTENTION MODULE                               │    │
│   │                                                                    │    │
│   │  Q (Query)  ──────┐                                               │    │
│   │                   ├──▶  softmax(QK^T × σ) ──▶ Attention Weights   │    │
│   │  K (Keys)   ──────┘                                               │    │
│   │                                                                    │    │
│   │  V (Values) ──────────▶  Weighted Synthesis ──▶ Config Output     │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│          ┌────────────────────────┼────────────────────────┐                │
│          ▼                        ▼                        ▼                │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐          │
│   │ DIVERGENCE  │         │  PRUNING    │         │  MUTATION   │          │
│   │   MODULE    │         │   MODULE    │         │   ENGINE    │          │
│   │             │         │             │         │             │          │
│   │ Generate k  │         │ Remove low  │         │ Semantic    │          │
│   │ branches    │         │ attention   │         │ Structural  │          │
│   │ per node    │         │ branches    │         │ Procedural  │          │
│   └─────────────┘         └─────────────┘         └─────────────┘          │
│                                   │                                          │
│                                   ▼                                          │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                      HEALING ENGINE                                │    │
│   │                                                                    │    │
│   │  • Repair missing components     • Resolve contradictions         │    │
│   │  • Restore coherent structure    • Validate reasoning paths       │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼                                          │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    MULTI-AGENT LAYER                               │    │
│   │                                                                    │    │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐              │    │
│   │  │ Marcus  │  │Victoria │  │  Derek  │  │  Luna   │              │    │
│   │  │Supervisor│  │Architect│  │Developer│  │   QA    │              │    │
│   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘              │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼                                          │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                   SUPERVISOR (META-AGENT)                          │    │
│   │                                                                    │    │
│   │  • Orchestrate reasoning cycles    • Aggregate agent outputs      │    │
│   │  • Enforce quality gates           • Manage escalation ladder     │    │
│   │  • Track evolution outcomes        • Report feedback signals      │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                           ┌─────────────────────────┐
                           │    FINAL SOLUTION       │
                           │   Generated Code +      │
                           │   Configuration         │
                           └─────────────────────────┘
```

### 2.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW DIAGRAM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User Request                                                               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────┐                                                       │
│   │ Query Embedding │ ─────────────────────────────────────┐                │
│   └────────┬────────┘                                      │                │
│            │                                               │                │
│            ▼                                               │                │
│   ┌─────────────────┐    ┌─────────────────┐              │                │
│   │  Option Pool    │───▶│  Key Embeddings │──────────────┤                │
│   │ (Static + Evol) │    └─────────────────┘              │                │
│   └─────────────────┘                                      │                │
│                                                           ▼                │
│                                              ┌─────────────────────┐        │
│                                              │ Attention Mechanism │        │
│                                              │  softmax(QK^T × σ)  │        │
│                                              └──────────┬──────────┘        │
│                                                         │                   │
│           ┌─────────────────────────────────────────────┼───────┐          │
│           │                                             │       │          │
│           ▼                                             ▼       ▼          │
│   ┌───────────────┐                           ┌────────────┐ ┌────────┐   │
│   │ Entropy Check │                           │  Weights   │ │ Scores │   │
│   └───────┬───────┘                           └─────┬──────┘ └────────┘   │
│           │                                         │                      │
│     Low ◀─┼─▶ High                                  │                      │
│           │                                         ▼                      │
│   ┌───────┴───────┐                       ┌─────────────────┐              │
│   │   Standard    │                       │ V-Value Blend   │              │
│   │     Mode      │                       │ (JSON Synthesis)│              │
│   │   (σ=20.0)    │                       └────────┬────────┘              │
│   │       OR      │                                │                       │
│   │ Combinational │                                ▼                       │
│   │     Mode      │                       ┌─────────────────┐              │
│   │   (σ=2.0)     │                       │  Synthesized    │              │
│   └───────────────┘                       │  Configuration  │              │
│                                           └────────┬────────┘              │
│                                                    │                       │
│                                                    ▼                       │
│                                           ┌─────────────────┐              │
│                                           │ Evolution Layer │              │
│                                           │ (Track + Learn) │              │
│                                           └────────┬────────┘              │
│                                                    │                       │
│                                                    ▼                       │
│                                           ┌─────────────────┐              │
│                                           │ Agent Execution │              │
│                                           └────────┬────────┘              │
│                                                    │                       │
│                                                    ▼                       │
│                                           ┌─────────────────┐              │
│                                           │ Outcome Feedback│──────────────┐
│                                           └─────────────────┘              │
│                                                                            │
│                                                    ┌───────────────────────┘
│                                                    ▼                       │
│                                           ┌─────────────────┐              │
│                                           │ V-Vector Store  │              │
│                                           │ (EMA Updates)   │              │
│                                           └─────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Minimal Working Example

This code block demonstrates the complete ArborMind reasoning pipeline:

```python
from arbormind import ArborTree, Node, Divergence, Attention, Mutation, Healing

# ═══════════════════════════════════════════════════════════════════════════
# 1. CREATE ROOT PROBLEM
# ═══════════════════════════════════════════════════════════════════════════
# The root node represents the initial problem statement
root = Node("Design an ecommerce backend")

# ═══════════════════════════════════════════════════════════════════════════
# 2. INITIALIZE TREE
# ═══════════════════════════════════════════════════════════════════════════
# The ArborTree manages the reasoning structure
tree = ArborTree(root)

# ═══════════════════════════════════════════════════════════════════════════
# 3. EXPAND BRANCHES (DIVERGENCE)
# ═══════════════════════════════════════════════════════════════════════════
# Generate k alternative reasoning paths
# - k=3: Create 3 different approaches to the problem
# - temperature: Creativity intensity (higher = more diverse branches)
tree.expand(Divergence(k=3, temperature=0.7))

# After expansion, tree might look like:
#   Root: "Design an ecommerce backend"
#   ├── Branch A: "Microservices architecture with event-driven design"
#   ├── Branch B: "Monolithic FastAPI with modular structure"
#   └── Branch C: "Serverless functions with GraphQL gateway"

# ═══════════════════════════════════════════════════════════════════════════
# 4. SCORE BRANCHES (ATTENTION)
# ═══════════════════════════════════════════════════════════════════════════
# Apply attention mechanism to compute relevance scores
# Uses: Attention(Q,K,V) = softmax(QK^T × σ)V
tree.score(Attention(
    relevance_weight=0.4,    # How relevant is this to the query?
    coherence_weight=0.3,    # Does this make logical sense?
    novelty_weight=0.2,      # Is this creative/non-obvious?
    cost_weight=0.1          # Is this resource-efficient?
))

# After scoring:
#   Branch A: attention=0.65 (high relevance, but complex)
#   Branch B: attention=0.85 (best balance of simplicity and capability)
#   Branch C: attention=0.45 (innovative but overkill for requirements)

# ═══════════════════════════════════════════════════════════════════════════
# 5. PRUNE WEAK BRANCHES
# ═══════════════════════════════════════════════════════════════════════════
# Remove branches below attention threshold to focus computation
tree.prune(threshold=0.5)

# After pruning:
#   Branch A: KEPT (0.65 > 0.5)
#   Branch B: KEPT (0.85 > 0.5)
#   Branch C: PRUNED (0.45 < 0.5)

# ═══════════════════════════════════════════════════════════════════════════
# 6. MUTATE PROMISING BRANCHES
# ═══════════════════════════════════════════════════════════════════════════
# Apply transformations to explore variations of top branches
tree.mutate(strategy=Mutation(
    semantic=True,      # Change meaning/approach
    structural=True,    # Change organization/architecture
    procedural=False,   # Don't change process order
    aesthetic=False     # Don't change style/formatting
))

# After mutation:
#   Branch B now has a variant:
#   └── Branch B': "Monolithic FastAPI with async background tasks"

# ═══════════════════════════════════════════════════════════════════════════
# 7. HEAL BROKEN REASONING
# ═══════════════════════════════════════════════════════════════════════════
# Repair missing components, resolve contradictions, restore coherence
tree.heal()

# Healing might:
#   - Add missing authentication layer to Branch A
#   - Resolve conflict between sync/async in Branch B'
#   - Fill in undefined database schema references

# ═══════════════════════════════════════════════════════════════════════════
# 8. CONVERGE ON BEST PATH
# ═══════════════════════════════════════════════════════════════════════════
# Synthesize final solution from highest-attention path(s)
solution = tree.converge()

# ═══════════════════════════════════════════════════════════════════════════
# 9. OUTPUT RESULT
# ═══════════════════════════════════════════════════════════════════════════
print(solution.output)
# Output: Complete ecommerce backend specification with:
#   - FastAPI application structure
#   - MongoDB/Beanie models for products, orders, users
#   - CRUD routers with async endpoints
#   - JWT authentication layer
#   - Background task handlers for order processing

print(solution.metadata)
# {
#     "selected_branch": "B'",
#     "attention_score": 0.88,
#     "mutations_applied": ["async_background_tasks"],
#     "healing_actions": ["add_auth_layer", "resolve_async_conflict"],
#     "decision_id": "dec_a1b2c3d4"  # For tracking outcomes
# }
```

### Real-World Integration Example

Here's how ArborMind is actually used within GenCode Studio:

```python
from app.arbormind import (
    ArborMindRouter,
    arbormind_route,
    compute_archetype_routing,
    report_routing_outcome
)

# ═══════════════════════════════════════════════════════════════════════════
# EXAMPLE 1: Tool Selection for a Code Generation Step
# ═══════════════════════════════════════════════════════════════════════════

router = ArborMindRouter()

# Define available tools with semantic descriptions and configurations
tool_options = [
    {
        "id": "syntax_fix",
        "description": "Fix Python/JavaScript syntax errors, typos, and formatting issues",
        "value": {"max_edits": 2, "apply_diff": True, "mode": "strict"}
    },
    {
        "id": "logic_fix",
        "description": "Fix logical errors, incorrect algorithms, and wrong business logic",
        "value": {"max_edits": 5, "apply_diff": False, "mode": "creative"}
    },
    {
        "id": "dependency_fix",
        "description": "Fix import errors, missing dependencies, and module resolution",
        "value": {"max_edits": 3, "apply_diff": True, "mode": "strict"}
    }
]

# Route the error to the best repair strategy
result = await router.route(
    query="TypeError: Cannot read property 'map' of undefined in useEffect",
    options=tool_options,
    context_type="error_routing",
    archetype="admin_dashboard"
)

print(result)
# {
#     "selected": "logic_fix",
#     "confidence": 0.78,
#     "value": {"max_edits": 4.2, "apply_diff": False, "mode": "creative"},
#     "decision_id": "dec_xyz123",
#     "evolved": True
# }

# After execution, report the outcome for learning
report_routing_outcome(
    decision_id=result["decision_id"],
    success=True,
    quality_score=8.5,
    details="Error fixed on first attempt"
)
```

---

## 4. API Reference

### 4.1 Node Class

```python
@dataclass
class Node:
    """
    Represents a single node in the ArborMind reasoning tree.
    
    A node encapsulates a reasoning step or decision point with
    its semantic embedding, attention score, and relationships.
    """
    
    # Core Content
    content: str                    # Natural language description of this reasoning step
    embedding: List[float]          # 768-dim vector (Gemini) or 1536-dim (OpenAI)
    
    # Attention State
    attention: float = 0.0          # Computed attention score [0.0, 1.0]
    mode: str = "standard"          # "standard" | "combinational" | "exploratory"
    
    # Tree Structure
    parent: Optional["Node"] = None  # Parent node (None for root)
    children: List["Node"] = None    # Child nodes (branch expansions)
    
    # Metadata
    id: str = None                   # Unique identifier (auto-generated)
    created_at: datetime = None      # Creation timestamp
    metadata: Dict[str, Any] = None  # Arbitrary key-value storage
    
    # Evolution Tracking
    evolved: bool = False            # Whether evolution was applied
    evolution_delta: Dict = None     # Changes from base configuration
```

### 4.2 ArborTree Class

```python
class ArborTree:
    """
    The central reasoning structure for ArborMind.
    
    Manages a tree of nodes representing alternative reasoning paths,
    with methods for expansion, scoring, pruning, mutation, and convergence.
    """
    
    def __init__(self, root: Node):
        """Initialize tree with a root problem node."""
        self.root = root
        self.nodes: Dict[str, Node] = {}
        self.active_branch_ids: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def expand(self, divergence: Divergence) -> List[Node]:
        """
        Generate child branches from each active node.
        
        Args:
            divergence: Divergence configuration
            
        Returns:
            List of newly created child nodes
        """
        pass
    
    def score(self, attention: Attention) -> Dict[str, float]:
        """
        Compute attention scores for all active nodes.
        
        Uses scaled dot-product attention:
            score = softmax(QK^T × σ)
        
        Args:
            attention: Attention configuration with weights
            
        Returns:
            Dict mapping node IDs to attention scores
        """
        pass
    
    def prune(self, threshold: float = None) -> List[str]:
        """
        Remove branches below attention threshold.
        
        Args:
            threshold: Minimum attention score to keep (default: 0.1)
            
        Returns:
            List of pruned node IDs
        """
        pass
    
    def mutate(self, strategy: Mutation = None) -> List[Node]:
        """
        Apply transformations to promising branches.
        
        Args:
            strategy: Mutation configuration (types to apply)
            
        Returns:
            List of newly created mutant nodes
        """
        pass
    
    def heal(self) -> Dict[str, List[str]]:
        """
        Repair broken reasoning paths.
        
        Behaviors:
        - Repair missing components
        - Resolve contradictions
        - Restore coherent structure
        - Validate logical consistency
        
        Returns:
            Dict mapping node IDs to list of healing actions applied
        """
        pass
    
    def converge(self) -> Solution:
        """
        Synthesize final solution from highest-scoring path(s).
        
        Returns:
            Solution object with output, metadata, and decision_id
        """
        pass
```

### 4.3 Modules

#### 4.3.1 Divergence Module

```python
@dataclass
class Divergence:
    """
    Configuration for branch expansion (divergent thinking).
    
    Controls how many and what kind of alternative reasoning
    paths are generated from each node.
    """
    
    k: int = 3
    """Number of child branches to generate per node.
    
    Recommended values:
    - k=2: Binary decisions (A/B testing)
    - k=3: Standard exploration (default)
    - k=5: Broad exploration (complex problems)
    """
    
    temperature: float = 0.7
    """Creativity intensity for branch generation.
    
    Range: [0.0, 2.0]
    - 0.0-0.3: Conservative, similar branches
    - 0.4-0.7: Balanced exploration (default)
    - 0.8-1.2: Creative, diverse branches
    - 1.3-2.0: Radical, potentially incoherent
    """
    
    max_depth: int = 5
    """Maximum tree depth to prevent runaway expansion."""
    
    focus_keywords: List[str] = None
    """Optional keywords to bias branch content."""
```

#### 4.3.2 Attention Module

```python
@dataclass
class Attention:
    """
    Configuration for attention-based scoring.
    
    Weights control the relative importance of different
    scoring dimensions when computing attention.
    """
    
    relevance_weight: float = 0.4
    """Weight for semantic relevance to the original query.
    
    Higher values prioritize solutions that directly address
    the problem statement.
    """
    
    coherence_weight: float = 0.3
    """Weight for logical consistency and structural soundness.
    
    Higher values prioritize well-reasoned, internally consistent
    solutions.
    """
    
    novelty_weight: float = 0.2
    """Weight for creative, non-obvious approaches.
    
    Higher values encourage exploration of unconventional solutions.
    """
    
    cost_weight: float = 0.1
    """Weight for resource efficiency (tokens, compute, complexity).
    
    Higher values favor simpler, more efficient solutions.
    """
    
    # Advanced Parameters
    scale_factor: float = 20.0
    """Sharpness of attention distribution (σ).
    
    - σ=20.0: Sharp (winner-takes-all) for standard mode
    - σ=2.0: Soft (blended) for combinational mode
    """
    
    min_score: float = 0.05
    """Minimum score threshold for inclusion in results."""
```

#### 4.3.3 Mutation Module

```python
@dataclass
class Mutation:
    """
    Configuration for branch transformation (mutation strategies).
    
    Different mutation types enable different kinds of exploration
    when the current solution space is insufficient.
    """
    
    semantic: bool = True
    """Apply semantic mutations (change meaning/approach).
    
    Examples:
    - "REST API" → "GraphQL API"
    - "Synchronous" → "Asynchronous"
    - "Monolithic" → "Microservices"
    """
    
    structural: bool = False
    """Apply structural mutations (change organization).
    
    Examples:
    - Reorder components
    - Split/merge modules
    - Change inheritance hierarchy
    """
    
    procedural: bool = False
    """Apply procedural mutations (change process order).
    
    Examples:
    - "Validate then process" → "Process then validate"
    - "Sync first" → "Async first"
    """
    
    aesthetic: bool = False
    """Apply aesthetic mutations (change style/formatting).
    
    Examples:
    - Change naming conventions
    - Alter code formatting style
    - Modify documentation style
    """
    
    intensity: float = 0.5
    """Mutation intensity [0.0, 1.0].
    
    - 0.0-0.3: Subtle variations
    - 0.4-0.6: Moderate changes (default)
    - 0.7-1.0: Radical transformations
    """
```

#### 4.3.4 Healing Module

```python
class Healing:
    """
    Healing module for repairing broken reasoning paths.
    
    Automatically detects and fixes issues in the reasoning tree
    to maintain coherent, complete solutions.
    """
    
    # Healing Behaviors
    
    def repair_missing_components(self, node: Node) -> List[str]:
        """
        Identify and fill gaps in the reasoning.
        
        Examples:
        - Add missing error handling
        - Fill undefined references
        - Complete partial implementations
        
        Returns:
            List of repair actions taken
        """
        pass
    
    def resolve_contradictions(self, node: Node) -> List[str]:
        """
        Detect and resolve logical conflicts.
        
        Examples:
        - Sync vs async conflicts
        - Type mismatches
        - Circular dependencies
        
        Returns:
            List of resolution actions taken
        """
        pass
    
    def restore_coherent_structure(self, node: Node) -> List[str]:
        """
        Ensure overall structure is sound.
        
        Examples:
        - Fix broken parent-child relationships
        - Repair dangling references
        - Validate tree integrity
        
        Returns:
            List of restoration actions taken
        """
        pass
    
    def validate_reasoning(self, node: Node) -> ValidationResult:
        """
        Check if reasoning path is valid and complete.
        
        Returns:
            ValidationResult with is_valid and issues list
        """
        pass
```

### 4.4 ArborMindRouter Class

```python
class ArborMindRouter:
    """
    Universal Attention-Based Decision Making Service.
    
    The production router used for all ArborMind decisions
    within GenCode Studio. Integrates with self-evolution layer.
    """
    
    async def route(
        self,
        query: str,
        options: List[Dict],
        top_k: int = 5,
        min_conf: float = 0.05,
        context_type: str = "general",
        archetype: str = "unknown"
    ) -> Dict:
        """
        Route a query to the best matching options.
        
        Args:
            query: The input text (user request, error log, etc.)
            options: List of dicts with 'id', 'description', and 'value'
            top_k: Number of top results to return
            min_conf: Minimum confidence threshold
            context_type: Type of decision context
            archetype: Project archetype
            
        Returns:
            {
                "selected": str,        # Best match ID
                "confidence": float,    # Score [0.0, 1.0]
                "ranked": List[Dict],   # All matches with scores
                "value": Dict,          # Synthesized configuration
                "decision_id": str,     # For outcome tracking
                "evolved": bool         # Whether evolution applied
            }
        """
        pass
```

---

## 5. State Machine Diagram

### 5.1 Reasoning Cycle State Machine

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        ARBORMIND STATE MACHINE                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

                              ┌───────────────┐
                              │     START     │
                              └───────┬───────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│                              ┌───────────────┐                                │
│            ┌─────────────────│   DIVERGE     │                                │
│            │                 │               │                                │
│            │                 │ Generate k    │                                │
│            │                 │ alternatives  │                                │
│            │                 └───────┬───────┘                                │
│            │                         │                                        │
│            │                         ▼                                        │
│            │                 ┌───────────────┐                                │
│            │                 │    SCORE      │                                │
│            │                 │               │                                │
│            │                 │ Calculate     │                                │
│            │                 │ attention     │                                │
│            │                 └───────┬───────┘                                │
│            │                         │                                        │
│            │                         ▼                                        │
│            │                 ┌───────────────┐                                │
│            │                 │    PRUNE      │                                │
│            │                 │               │                                │
│            │                 │ Suppress or   │                                │
│            │                 │ delete weak   │                                │
│            │                 │ branches      │                                │
│            │                 └───────┬───────┘                                │
│            │                         │                                        │
│            │                         ▼                                        │
│            │                 ┌───────────────┐                                │
│            │                 │   MUTATE      │◀───────────────────────────┐   │
│            │                 │               │                            │   │
│            │                 │ Transform     │                            │   │
│            │                 │ reasoning     │                            │   │
│            │                 └───────┬───────┘                            │   │
│            │                         │                                    │   │
│            │                         ▼                                    │   │
│            │                 ┌───────────────┐                            │   │
│            │                 │    HEAL       │                            │   │
│            │                 │               │                            │   │
│            │                 │ Repair broken │                            │   │
│            │                 │ logic         │                            │   │
│            │                 └───────┬───────┘                            │   │
│            │                         │                                    │   │
│            │                         ▼                                    │   │
│            │                 ┌───────────────┐     No                     │   │
│            │                 │  SYNTHESIZE   │────────────────────────────┘   │
│            │                 │               │  (Not converged)               │
│            │                 │ Blend branches│                                │
│            │                 └───────┬───────┘                                │
│            │                         │ Yes (Converged)                        │
│            │                         ▼                                        │
│            │                 ┌───────────────┐                                │
│            └────────────────▶│     END       │                                │
│                (Retry)       │               │                                │
│                              │ Convergence   │                                │
│                              │ achieved      │                                │
│                              └───────────────┘                                │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 State Descriptions

| State | Description | Entry Condition | Exit Condition |
|:------|:------------|:----------------|:---------------|
| **START** | Initialize tree with root problem | User request received | Root node created |
| **DIVERGE** | Generate alternative reasoning paths | Tree needs expansion | k branches created per node |
| **SCORE** | Compute attention scores for all nodes | Branches exist | All nodes have attention scores |
| **PRUNE** | Remove low-attention branches | Scores computed | Weak branches removed |
| **MUTATE** | Transform promising branches | Pruning complete | Mutations applied to top branches |
| **HEAL** | Repair broken reasoning paths | Mutations applied | All paths validated |
| **SYNTHESIZE** | Blend top branches into solution | Healing complete | Solution synthesized OR retry needed |
| **END** | Return final solution | Convergence achieved | Solution delivered |

### 5.3 Transition Rules

```python
# Pseudo-code for state transitions

def reasoning_cycle(root_problem: str) -> Solution:
    state = "START"
    tree = ArborTree(Node(root_problem))
    max_iterations = 10
    iteration = 0
    
    while state != "END" and iteration < max_iterations:
        iteration += 1
        
        if state == "START":
            state = "DIVERGE"
            
        elif state == "DIVERGE":
            tree.expand(Divergence(k=3))
            state = "SCORE"
            
        elif state == "SCORE":
            tree.score(Attention())
            state = "PRUNE"
            
        elif state == "PRUNE":
            tree.prune(threshold=0.1)
            if len(tree.active_nodes) == 0:
                # All branches pruned, need to diverge again
                state = "DIVERGE"
            else:
                state = "MUTATE"
                
        elif state == "MUTATE":
            if needs_mutation(tree):
                tree.mutate()
            state = "HEAL"
            
        elif state == "HEAL":
            tree.heal()
            state = "SYNTHESIZE"
            
        elif state == "SYNTHESIZE":
            result = tree.converge()
            if result.is_valid and result.confidence > 0.7:
                state = "END"
            elif iteration < max_iterations:
                state = "MUTATE"  # Retry with mutations
            else:
                state = "END"  # Force exit
    
    return result
```

---

## 6. Data Models & Internal Representations

### 6.1 Node Data Model

```python
@dataclass
class NodeData:
    """Internal representation of a reasoning node."""
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    id: str                           # Unique identifier (UUID4)
    content: str                      # Natural language content
    
    # ═══════════════════════════════════════════════════════════════════════
    # EMBEDDING
    # ═══════════════════════════════════════════════════════════════════════
    embedding: List[float]            # Semantic embedding vector
                                      # - Gemini: 768 dimensions
                                      # - OpenAI: 1536 dimensions
    
    # ═══════════════════════════════════════════════════════════════════════
    # ATTENTION
    # ═══════════════════════════════════════════════════════════════════════
    attention: float                  # Computed attention score [0.0, 1.0]
    raw_score: float                  # Pre-softmax similarity score
    entropy: float                    # Distribution entropy (for mode detection)
    
    # ═══════════════════════════════════════════════════════════════════════
    # STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════
    parent_id: Optional[str]          # Parent node ID (None for root)
    children_ids: List[str]           # Child node IDs
    depth: int                        # Tree depth (root = 0)
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATE
    # ═══════════════════════════════════════════════════════════════════════
    status: str                       # "active" | "pruned" | "mutated" | "healed"
    mode: str                         # "standard" | "combinational" | "exploratory"
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


# JSON Serialization Example:
"""
{
    "id": "node_a1b2c3d4",
    "content": "Use FastAPI with async endpoints for the backend",
    "embedding": [0.0234, -0.1892, 0.4521, ...],  # 768 values
    "attention": 0.85,
    "raw_score": 0.72,
    "entropy": 0.42,
    "parent_id": "node_root123",
    "children_ids": ["node_x1y2z3", "node_p4q5r6"],
    "depth": 1,
    "status": "active",
    "mode": "standard",
    "created_at": "2024-12-12T10:30:00Z",
    "updated_at": "2024-12-12T10:35:00Z",
    "metadata": {
        "archetype": "admin_dashboard",
        "mutations_applied": ["semantic"],
        "healing_actions": []
    }
}
"""
```

### 6.2 Tree Data Model

```python
@dataclass
class TreeData:
    """Internal representation of the reasoning tree."""
    
    # ═══════════════════════════════════════════════════════════════════════
    # STRUCTURE
    # ═══════════════════════════════════════════════════════════════════════
    nodes: Dict[str, NodeData]        # All nodes indexed by ID
    root_id: str                      # Root node ID
    active_branch_ids: List[str]      # Currently active (not pruned) branches
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATE
    # ═══════════════════════════════════════════════════════════════════════
    current_state: str                # Current state machine state
    iteration: int                    # Current reasoning cycle iteration
    max_depth: int                    # Current maximum depth reached
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    total_nodes_created: int
    total_nodes_pruned: int
    total_mutations_applied: int
    total_healing_actions: int
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    metadata: Dict[str, Any]


# JSON Serialization Example:
"""
{
    "nodes": {
        "node_root123": {...},
        "node_a1b2c3d4": {...},
        "node_x1y2z3": {...}
    },
    "root_id": "node_root123",
    "active_branch_ids": ["node_a1b2c3d4", "node_x1y2z3"],
    "current_state": "SCORE",
    "iteration": 2,
    "max_depth": 3,
    "total_nodes_created": 15,
    "total_nodes_pruned": 8,
    "total_mutations_applied": 3,
    "total_healing_actions": 2,
    "metadata": {
        "archetype": "admin_dashboard",
        "decision_id": "dec_m1n2o3p4",
        "context_type": "architecture"
    }
}
"""
```

### 6.3 Decision Record Schema

```python
@dataclass
class DecisionRecord:
    """Persistent record of a routing decision for evolution learning."""
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    decision_id: str                  # Unique decision identifier
    query_hash: str                   # SHA256 hash of query (privacy)
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT
    # ═══════════════════════════════════════════════════════════════════════
    context_type: str                 # "tool_selection", "error_routing", etc.
    archetype: str                    # Project archetype
    
    # ═══════════════════════════════════════════════════════════════════════
    # DECISION
    # ═══════════════════════════════════════════════════════════════════════
    selected_option: str              # ID of selected option
    synthesized_value: Dict           # The V-vector configuration used
    attention_weights: Dict[str, float]  # Weight per option ID
    
    # ═══════════════════════════════════════════════════════════════════════
    # OUTCOME (filled later via feedback)
    # ═══════════════════════════════════════════════════════════════════════
    outcome: Optional[str]            # "success", "failure", "partial"
    outcome_score: Optional[float]    # Quality score [0.0, 10.0]
    outcome_details: Optional[str]    # Additional context
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIMESTAMPS
    # ═══════════════════════════════════════════════════════════════════════
    created_at: datetime
    outcome_at: Optional[datetime]
```

### 6.4 Evolved V-Vector Schema

```python
@dataclass
class EvolvedVector:
    """Learned V-vector adjustments from historical outcomes."""
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    context_key: str                  # "{context_type}:{archetype}:{option_id}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # VALUES
    # ═══════════════════════════════════════════════════════════════════════
    base_value: Dict                  # Original static V-vector
    evolved_value: Dict               # Learned adjusted V-vector
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    confidence: float                 # Based on sample size [0.0, 0.95]
    success_rate: float               # Historical success rate [0.0, 1.0]
    sample_count: int                 # Number of observations
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIMESTAMPS
    # ═══════════════════════════════════════════════════════════════════════
    created_at: datetime
    updated_at: datetime
```

---

## 7. Computational Complexity Analysis

### 7.1 Time Complexity

| Operation | Worst Case | Average Case | Notes |
|:----------|:-----------|:-------------|:------|
| **Tree Expansion (Diverge)** | O(b^d) | O(b^d) | b = branching factor, d = depth |
| **Attention Scoring** | O(n × m × d_k) | O(n × m × d_k) | n = queries, m = keys, d_k = embedding dim |
| **Pruning** | O(n) | O(n) | n = number of nodes |
| **Mutation** | O(n × k) | O(n × k) | n = nodes, k = mutation types |
| **Healing** | O(n × c) | O(n) | c = complexity of healing strategy |
| **Convergence** | O(p) | O(p) | p = nodes in selected path |

#### 7.1.1 Detailed Analysis

**Tree Expansion (Diverge):**
```
Time = O(b^d) where:
  b = branching factor (typically k=3)
  d = maximum depth (typically 3-5)

For k=3, d=5: O(3^5) = O(243) nodes maximum
```

**Attention Scoring:**
```
Time = O(n × m × d_k) where:
  n = number of query embeddings (typically 1)
  m = number of option embeddings (typically 5-30)
  d_k = embedding dimension (768 or 1536)

Matrix multiplication dominates:
  Q @ K^T: O(n × m × d_k)
  Softmax: O(n × m)
  Weighted sum: O(n × m × d_v)
```

**Pruning:**
```
Time = O(n) where:
  n = number of nodes to evaluate

Simple threshold comparison per node.
```

**Mutation:**
```
Time = O(n × k) where:
  n = number of nodes to mutate
  k = number of mutation types applied

Each mutation type requires O(1) transformation.
```

**Healing:**
```
Time = O(n × c) where:
  n = number of nodes to heal
  c = complexity of healing strategy

Simple repairs: O(1) per node
Complex repairs (e.g., contradiction resolution): O(n) worst case
```

### 7.2 Space Complexity

| Structure | Complexity | Notes |
|:----------|:-----------|:------|
| **Node Storage** | O(b^d) | Maximum nodes in tree |
| **Embedding Cache** | O(v × d_k) | v = unique embeddings, d_k = dimension |
| **Decision History** | O(h) | h = history entries (bounded by config) |
| **Evolved V-Vectors** | O(c × a × o) | c = contexts, a = archetypes, o = options |

#### 7.2.1 Detailed Analysis

**Node Storage:**
```
Space = O(b^d × S_node) where:
  b^d = maximum number of nodes
  S_node = size per node (content + embedding + metadata)
  
For k=3, d=5, d_k=768:
  S_node ≈ 500 bytes content + 768×4 bytes embedding + 200 bytes metadata
  S_node ≈ 3.7 KB per node
  
Maximum: 243 × 3.7 KB ≈ 900 KB
```

**Embedding Cache:**
```
Space = O(v × d_k × 4 bytes) where:
  v = number of unique texts cached (max 5000)
  d_k = embedding dimension (768 or 1536)
  
Maximum: 5000 × 768 × 4 = 15.4 MB
```

### 7.3 Mitigation Strategies

To prevent computational explosion, ArborMind employs several safeguards:

#### 7.3.1 Attention-Based Pruning
```python
# Aggressively prune low-attention branches
tree.prune(threshold=0.1)  # Remove branches with attention < 10%

# Effect: Exponential tree becomes effectively linear
# Instead of O(b^d), active nodes stay at O(d × surviving_ratio)
```

#### 7.3.2 Thresholding
```python
# Hard limits on tree size
MAX_NODES = 100
MAX_DEPTH = 5
MAX_CHILDREN_PER_NODE = 5

# Dynamic adjustment based on problem complexity
if estimated_complexity > HIGH_THRESHOLD:
    k = 2  # Reduce branching factor
```

#### 7.3.3 Sliding Windows
```python
# Only process most recent nodes in large trees
ACTIVE_WINDOW_SIZE = 20

# Archive old branches instead of keeping in memory
if len(tree.active_nodes) > ACTIVE_WINDOW_SIZE:
    archive_lowest_attention_nodes(tree, keep=ACTIVE_WINDOW_SIZE)
```

#### 7.3.4 Lazy Embedding Computation
```python
# Only compute embeddings when needed
async def get_embedding_lazy(text: str) -> List[float]:
    if text in _embedding_cache:
        return _embedding_cache[text]  # O(1) lookup
    
    # Only compute if not cached
    embedding = await compute_embedding(text)  # O(d_k) API call
    _embedding_cache[text] = embedding
    return embedding
```

### 7.4 Practical Performance

**Typical Operation Times (measured on production system):**

| Operation | Latency (p50) | Latency (p99) |
|:----------|:--------------|:--------------|
| Single Routing Decision | 45ms | 120ms |
| Full Reasoning Cycle | 200ms | 500ms |
| Embedding API Call | 80ms | 200ms |
| Cache Hit | 0.1ms | 0.5ms |
| V-Vector Evolution Update | 5ms | 15ms |

---

## 8. Example Reasoning Cycle Breakdown

### 8.1 Problem Statement

**User Request:** "Generate backend + frontend for a booking system"

### 8.2 Step-by-Step Execution

#### Step 1: DIVERGE — Generate 3 Alternative Branches

```
Root: "Generate backend + frontend for a booking system"
│
├── Branch A: "Monolithic FastAPI + React SPA"
│   Description: Single FastAPI backend with React frontend,
│   all deployable as one unit with shared authentication.
│
├── Branch B: "Microservices + Next.js SSR"
│   Description: Separate services for bookings, users, payments
│   with Next.js frontend for SEO and SSR benefits.
│
└── Branch C: "Serverless + Static Site"
│   Description: AWS Lambda functions + static React site,
│   minimal infrastructure, pay-per-use pricing.
```

#### Step 2: SCORE — Compute Attention Scores

```python
# Query embedding for "booking system"
Q = get_embedding("Generate backend + frontend for a booking system")

# Key embeddings for each branch
K = [
    get_embedding("Monolithic FastAPI + React SPA..."),
    get_embedding("Microservices + Next.js SSR..."),
    get_embedding("Serverless + Static Site...")
]

# Attention computation
scores = softmax(Q @ K.T × 20.0)

# Results:
#   Branch A: attention = 0.72  (Best match: simple, proven pattern)
#   Branch B: attention = 0.21  (Good but overkill for typical booking)
#   Branch C: attention = 0.07  (Poor: booking systems need state)
```

| Branch | Attention Score | Reasoning |
|:-------|:----------------|:----------|
| A (Monolithic) | **0.72** | Best fit: Simple architecture for booking CRUD |
| B (Microservices) | 0.21 | Overengineered for scope |
| C (Serverless) | 0.07 | Stateless doesn't suit booking workflows |

#### Step 3: PRUNE — Remove Low-Attention Branches

```
Threshold: 0.15

Before Pruning:
├── Branch A: 0.72 → KEEP
├── Branch B: 0.21 → KEEP
└── Branch C: 0.07 → PRUNED ❌

After Pruning:
├── Branch A: 0.72 (active)
└── Branch B: 0.21 (active)
```

#### Step 4: MUTATE — Transform Branch A

The system applies a **semantic mutation** to Branch A because it's the top candidate but could benefit from enhancement:

```
Original Branch A:
"Monolithic FastAPI + React SPA with shared authentication"

Mutation Applied: SEMANTIC (async pattern injection)

Mutated Branch A':
"Monolithic FastAPI + React SPA with:
 - Async background tasks for email notifications
 - Redis caching for availability lookups
 - WebSocket for real-time booking updates"
```

**Mutation Details:**
```python
Mutation(
    semantic=True,   # ✓ Add async patterns
    structural=False,
    procedural=False,
    aesthetic=False
)
```

#### Step 5: HEAL — Repair Missing Components

The Healing Engine identifies gaps in Branch A':

```
Healing Actions:
1. ✓ Add authentication layer (was implicit, now explicit JWT)
2. ✓ Add availability conflict detection (prevent double-booking)
3. ✓ Add timezone handling (booking systems need this)
4. ✓ Resolve Redis/MongoDB consistency (added cache invalidation)

Healed Branch A'':
"Monolithic FastAPI + React SPA with:
 - JWT authentication with refresh tokens
 - Async background tasks for email notifications
 - Redis caching for availability lookups
 - WebSocket for real-time booking updates
 - Availability conflict detection
 - Timezone-aware datetime handling
 - Cache invalidation on booking changes"
```

#### Step 6: SYNTHESIZE — Blend and Converge

Since Branch A'' scores highest (0.85 after healing), it's selected as the primary solution. However, Branch B contributed an insight about SSR that's blended in:

```python
# Final Synthesized Configuration
synthesized_value = {
    "architecture": "monolithic",
    "backend_framework": "fastapi",
    "frontend_framework": "react",
    "database": "mongodb",
    "cache": "redis",
    "auth": "jwt",
    "realtime": "websocket",
    "features": [
        "availability_conflict_detection",
        "timezone_handling",
        "cache_invalidation",
        "email_notifications"
    ],
    # Blended from Branch B (0.21 weight contribution):
    "seo_friendly_pages": ["landing", "pricing"],  # Partial SSR for key pages
}
```

#### Step 7: Final Output

```json
{
    "solution": {
        "backend": {
            "framework": "FastAPI",
            "models": ["Booking", "User", "Resource", "Availability"],
            "routers": ["bookings", "users", "resources", "auth"],
            "dependencies": ["mongodb", "redis", "jwt", "celery"]
        },
        "frontend": {
            "framework": "React 18",
            "components": ["BookingForm", "Calendar", "UserDashboard"],
            "state": "React Query + Context"
        }
    },
    "metadata": {
        "selected_branch": "A''",
        "attention_score": 0.85,
        "branches_explored": 3,
        "branches_pruned": 1,
        "mutations_applied": ["semantic_async"],
        "healing_actions": [
            "add_auth_layer",
            "add_conflict_detection",
            "add_timezone_handling",
            "add_cache_invalidation"
        ],
        "decision_id": "dec_booking123"
    }
}
```

### 8.3 Visual Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BOOKING SYSTEM REASONING TRACE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DIVERGE        SCORE         PRUNE        MUTATE       HEAL            │
│                                                                          │
│     A  ─────── 0.72 ─────── KEEP ─────── A' ─────── A'' ────┐           │
│    ╱                                                         │           │
│  Root          B  ─────── 0.21 ─────── KEEP ─────── (blend) ─┼──▶ OUTPUT│
│    ╲                                                         │           │
│     C  ─────── 0.07 ─────── PRUNED ❌                        │           │
│                                                              │           │
└──────────────────────────────────────────────────────────────┴───────────┘
```

---

## 9. Background and Related Work

### 2.1 Attention Mechanisms in NLP

The transformer architecture introduced by Vaswani et al. (2017) revolutionized natural language processing through the scaled dot-product attention mechanism:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

This mechanism enables dynamic weighting of input sequences based on query relevance. While primarily used for sequence-to-sequence tasks, the underlying principle—computing weighted combinations based on semantic similarity—has broader applications.

### 2.2 Retrieval-Augmented Generation (RAG)

RAG systems (Lewis et al., 2020) use embedding-based retrieval to augment LLM context. However, traditional RAG exhibits a critical constraint: **V = K**. The retrieved values are the same embeddings used for matching, limiting the system to returning documents rather than arbitrary behaviors.

### 2.3 Multi-Agent Systems

Recent work on multi-agent code generation (AutoGen, MetaGPT, CrewAI) demonstrates the power of specialized agents collaborating on complex tasks. However, these systems typically use:
- Fixed agent selection rules
- Static capability definitions
- Manual coordination protocols

ArborMind extends this paradigm by making agent coordination itself an attention-weighted, learnable process.

### 2.4 Self-Evolving AI Systems

Research on continual learning and adaptive systems (Parisi et al., 2019) explores how neural networks can improve over time. ArborMind applies these principles at the orchestration level, evolving decision-making policies rather than model weights.

---

## 3. The ArborMind Architecture

### 3.1 System Overview

ArborMind operates as an intelligent middleware layer within the FAST v2 code generation engine. It intercepts decision points throughout the workflow and provides attention-based routing with self-evolution capabilities.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ArborMind Framework                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Query (Q)  │    │   Keys (K)   │    │  Values (V)  │               │
│  │  User Request│    │  Semantic    │    │    JSON      │               │
│  │  Error Log   │    │  Descriptions│    │   Configs    │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         └───────────────────┼───────────────────┘                        │
│                             ▼                                            │
│                  ┌─────────────────────┐                                 │
│                  │  Attention Router   │                                 │
│                  │  softmax(QK^T × σ)V │                                 │
│                  └──────────┬──────────┘                                 │
│                             │                                            │
│              ┌──────────────┼──────────────┐                             │
│              ▼              ▼              ▼                             │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐                      │
│     │    C-AM    │  │    E-AM    │  │    T-AM    │                      │
│     │Combinational│  │ Exploratory│  │Transformational│                  │
│     │   Blend    │  │   Inject   │  │   Mutate   │                      │
│     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                      │
│           │               │               │                              │
│           └───────────────┼───────────────┘                              │
│                           ▼                                              │
│                  ┌─────────────────────┐                                 │
│                  │  Synthesized Config │                                 │
│                  │  {mode, params, ...}│                                 │
│                  └──────────┬──────────┘                                 │
│                             │                                            │
│                             ▼                                            │
│                  ┌─────────────────────┐                                 │
│                  │  Evolution Layer    │                                 │
│                  │  Track → Learn →    │                                 │
│                  │  Evolve V-Vectors   │                                 │
│                  └─────────────────────┘                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Core Components

#### 3.2.1 Attention Router (`router.py`)

The central intelligence that computes attention-weighted configurations:

```python
class AttentionRouter:
    """
    Universal Service for Attention-Based Decision Making.
    
    Implements: Attention(Q,K,V) = softmax(QK^T × σ)V
    Where V ≠ K (Values are JSON configs, not embeddings)
    """
    
    async def route(
        self,
        query: str,
        options: List[Dict],
        context_type: str,
        archetype: str
    ) -> Dict:
        # 1. Embed query
        Q = await get_embedding(query)
        
        # 2. Embed option descriptions (Keys)
        K = await embed_options(options)
        
        # 3. Apply evolution layer
        evolved_options = self.evolution_manager.evolve(options)
        
        # 4. Compute attention with custom scaling
        weights = creative_attention(Q, K, mode="standard")
        
        # 5. Synthesize weighted configuration
        synthesized = blend_values(weights, evolved_options)
        
        # 6. Track decision for learning
        decision_id = self.track_decision(query, synthesized)
        
        return {
            "selected": top_option,
            "value": synthesized,
            "decision_id": decision_id,
            "evolved": True
        }
```

#### 3.2.2 Evolution Layer (`evolution.py`)

Manages the learning loop that improves routing over time:

```python
class AttentionEvolution:
    """
    Bridge between the V-Vector Store and the Router.
    
    Responsibilities:
    1. Apply learned adjustments before routing
    2. Track decisions with unique IDs
    3. Process outcome feedback for learning
    """
    
    def evolve_options(self, options: List[Dict]) -> List[Dict]:
        """Apply EMA-adjusted V-vectors to static options."""
        return self.store.get_adjustment_for_options(
            context_type, archetype, options
        )
    
    def report_outcome(self, decision_id: str, success: bool, score: float):
        """Feed outcome back into the learning system."""
        self.store.record_outcome(decision_id, success, score)
```

#### 3.2.3 Explorer (`explorer.py`)

Implements E-AM by searching for foreign patterns:

```python
async def inject_foreign_patterns(
    archetype: str,
    error_text: str
) -> Dict:
    """
    E-AM: Inject patterns from foreign archetypes.
    
    When standard strategies fail, search for similar errors
    in DIFFERENT project types and blend their solutions.
    """
    # Search V-Vector store for patterns from other archetypes
    candidates = await store.search_patterns(
        query=error_text,
        exclude_archetype=archetype
    )
    
    # Compute attention over foreign patterns
    att = creative_attention(Q, K, values, mode="combinational")
    
    return {
        "patterns": candidates,
        "blended_value": blend_values(att["weights"], values),
        "source_archetypes": [c["archetype"] for c in candidates]
    }
```

### 3.3 Decision Points

ArborMind intercepts the following decision points in the FAST v2 workflow:

| Decision Point | Location | What Gets Routed |
|:--------------|:---------|:-----------------|
| **Tool Selection** | `registry.py` | Which tools to inject into agent context |
| **File Context** | `prompt_management.py` | Which files to include in context window |
| **Error Strategy** | `error_router.py` | How to handle specific error patterns |
| **Supervision Policy** | `supervisor.py` | Retry, heal, or abort decisions |
| **Archetype Detection** | `router.py` | Project type classification |
| **UI Vibe Selection** | `router.py` | Design aesthetic routing |

---

## 4. Mathematical Foundation: V≠K Attention

### 4.1 The V≠K Innovation

Traditional attention uses:
$$V = K = \text{Embeddings}$$

ArborMind decouples Values from Keys:
- **K (Keys)**: Unit-normalized semantic embeddings of option descriptions
- **V (Values)**: Arbitrary JSON configuration objects

This enables the attention mechanism to synthesize *behaviors* rather than just retrieve *documents*.

### 4.2 Custom Scaling Factor

Standard attention scaling ($\frac{1}{\sqrt{d_k}}$) assumes unstructured embedding spaces. Modern embedding APIs (OpenAI, Gemini) return **unit-normalized vectors**, making standard scaling produce overly soft distributions.

ArborMind uses a custom sharpness factor:

$$\text{Attention}(Q, K, V) = \text{softmax}\left((Q \cdot K^T) \times \sigma \right)V$$

Where:
- **σ = 20.0** for standard mode (sharp, winner-takes-all)
- **σ = 2.0** for combinational mode (soft, multi-source blending)

### 4.3 Entropy-Based Mode Detection

The system automatically detects when combinational mode is beneficial using entropy:

$$H = -\sum_{i} w_i \log(w_i)$$

Where $w_i$ are attention weights. High entropy indicates the query spans multiple domains:

| Entropy | Interpretation | Action |
|:--------|:---------------|:-------|
| H < 0.5 | Confident single match | Use standard mode |
| 0.5 ≤ H < 1.5 | Moderate uncertainty | Use standard mode |
| H ≥ 1.5 | Multi-domain query | Switch to combinational |

### 4.4 Value Blending Algorithm

When synthesizing configurations from multiple options:

```python
def blend_values(weights: np.ndarray, values: List[Dict]) -> Dict:
    """
    Domain-general V-value synthesis.
    
    Blending rules:
    - Numeric fields: Weighted average
    - Boolean/String fields: Winner-takes-all
    - Missing keys: Graceful handling
    """
    output = {}
    for key in all_keys(values):
        vals = [v.get(key) for v in values]
        
        if all_numeric(vals):
            # Weighted average for numbers
            output[key] = sum(w * v for w, v in zip(weights, vals))
        else:
            # Winner-takes-all for non-numeric
            output[key] = vals[argmax(weights)]
    
    return output
```

**Example:**

Query: "Fix a performance issue in the admin dashboard"

Options with weights:
| Option | Weight | max_edits | apply_diff | mode |
|:-------|:-------|:----------|:-----------|:-----|
| syntax_fix | 0.15 | 2 | True | "strict" |
| logic_fix | 0.60 | 5 | False | "creative" |
| config_fix | 0.25 | 1 | True | "strict" |

Synthesized Config:
```json
{
  "max_edits": 3.55,  // Weighted average: 0.15*2 + 0.60*5 + 0.25*1
  "apply_diff": false, // Winner: logic_fix
  "mode": "creative"   // Winner: logic_fix
}
```

---

## 5. The Three AM Operators

### 5.1 C-AM: Combinational ArborMind

**Purpose:** Blend multiple archetypes/strategies when a single choice is insufficient.

**When Activated:**
- High entropy in attention distribution
- Context explicitly requires blending (e.g., "behavior_synthesis")
- User request spans multiple domains

**Mechanism:**
```python
# Standard mode (σ = 20.0) produces sharp weights:
# [0.95, 0.03, 0.02] → Winner takes all

# Combinational mode (σ = 2.0) produces soft weights:
# [0.45, 0.32, 0.23] → Blended output
```

**Example Use Case:**

A user requests: "Build a project management tool with real-time collaboration"

This spans two archetypes:
- `project_management`: Task boards, assignments, deadlines
- `realtime_collab`: WebSockets, presence indicators, live updates

C-AM blends both:
```json
{
  "archetype": "hybrid",
  "features": {
    "from_project_management": ["kanban_board", "task_assignment"],
    "from_realtime_collab": ["websocket_sync", "presence_api"]
  },
  "priority_weight": {
    "project_management": 0.55,
    "realtime_collab": 0.45
  }
}
```

### 5.2 E-AM: Exploratory ArborMind

**Purpose:** Inject patterns from foreign domains when standard approaches fail.

**When Activated:**
- Retry count reaches threshold (default: 2)
- Standard strategies have failed
- `enable_eam` configuration is true

**Mechanism:**

```python
async def decide_repair_strategy(..., retries: int):
    if retries >= settings.am.eam_retry_threshold:
        # Search foreign archetypes
        foreign = await inject_foreign_patterns(
            archetype=current_archetype,
            error_text=error_log
        )
        
        if foreign["patterns"]:
            # Blend foreign solutions with standard
            return merge_strategies(standard_result, foreign)
```

**Example Use Case:**

Error: `RecursionError: maximum recursion depth exceeded`  
Current Archetype: `admin_dashboard`

Standard fix strategies have failed twice. E-AM searches the V-Vector store and finds:

| Foreign Archetype | Pattern | Success Rate |
|:-----------------|:--------|:-------------|
| gaming | Iterative state machines | 0.85 |
| compiler | Tail call optimization | 0.78 |
| data_processing | Chunked iteration | 0.72 |

E-AM injects a hint into the repair prompt:
```
💡 FOREIGN PATTERN SUGGESTION (E-AM):
- From gaming: Consider converting recursive logic to iterative state machine
- From compiler: Tail-call optimization pattern may apply here
```

### 5.3 T-AM: Transformational ArborMind

**Purpose:** Mutate constraints when fundamentally blocked.

**When Activated:**
- Retry count reaches critical threshold (default: 3)
- All standard and exploratory strategies exhausted
- `enable_tam` configuration is true (default: false, requires sandbox)

**Mechanism:**

T-AM applies one of three mutation operators:

| Operator | Trigger Keywords | Action |
|:---------|:-----------------|:-------|
| **DROP** | strict, validation, schema, type | Remove constraints |
| **VARY** | timeout, memory, performance | Modify approach |
| **ADD** | not found, missing, undefined | Introduce capabilities |

```python
def _build_mutation(operator: str, error_log: str) -> Dict:
    if operator == "DROP":
        return {
            "strict_mode": False,
            "verify_types": False,
            "max_edits": 10  # Increased limit
        }
    elif operator == "VARY":
        return {
            "apply_diff": not current["apply_diff"],  # Toggle
            "force_rewrite": True,
            "max_edits": current["max_edits"] * 2
        }
    elif operator == "ADD":
        return {
            "allowed_imports": ["*"],  # Allow any import
            "use_external_lib": True,
            "search_solutions": True
        }
```

**Safety Controls:**

T-AM is protected by multiple safety layers:
1. **Feature Flag**: Disabled by default (`enable_tam: false`)
2. **Sandbox Requirement**: Mutations run in Docker sandbox first
3. **Approval Requirement**: Human approval required before applying
4. **Rollout Percentage**: Gradual rollout via `tam_rollout_pct`

**Example Use Case:**

After 3 failed attempts to fix a TypeScript type error:

```
🔮 CONSTRAINT MUTATION (T-AM):
Operator: DROP
Description: Dropped strict_mode and type verification
(You are authorized to bypass previous constraints)

Mutated Config:
- strict_mode: False → True
- verify_types: False → True
- max_edits: 3 → 10
```

### 5.4 Escalation Ladder

The three operators form a principled escalation path:

```
┌─────────────────────────────────────────────────────────────┐
│                    AM Escalation Ladder                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Retry 0-1    ┌────────────────────────────────────┐        │
│               │         Standard Routing            │        │
│               │   Sharp attention (σ = 20.0)        │        │
│               │   Winner-takes-all selection        │        │
│               └─────────────┬──────────────────────┘        │
│                             │ Failed?                        │
│                             ▼                                │
│  Retry 2      ┌────────────────────────────────────┐        │
│               │         C-AM + E-AM                 │        │
│               │   Soft attention (σ = 2.0)          │        │
│               │   Foreign pattern injection         │        │
│               └─────────────┬──────────────────────┘        │
│                             │ Failed?                        │
│                             ▼                                │
│  Retry 3+     ┌────────────────────────────────────┐        │
│               │           T-AM                      │        │
│               │   Constraint mutation               │        │
│               │   DROP / VARY / ADD operators       │        │
│               │   (Sandbox required)                │        │
│               └────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Self-Evolution Layer

### 6.1 Learning Loop

ArborMind implements a closed-loop learning system:

```
┌─────────────────────────────────────────────────────────────┐
│                    Self-Evolution Loop                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐            │
│   │  Static  │────▶│ Evolution│────▶│ Evolved  │            │
│   │ V-Vectors│     │  Layer   │     │ V-Vectors│            │
│   └──────────┘     └────┬─────┘     └────┬─────┘            │
│                         │                │                   │
│                         │                ▼                   │
│                         │         ┌──────────┐              │
│                         │         │ Attention │              │
│                         │         │  Router   │              │
│                         │         └────┬─────┘              │
│                         │              │                     │
│                         │              ▼                     │
│                         │         ┌──────────┐              │
│                         │         │ Decision │              │
│                         │         │ Tracking │              │
│                         │         └────┬─────┘              │
│                         │              │                     │
│                         │              ▼                     │
│                         │         ┌──────────┐              │
│                         │         │ Execution│              │
│                         │         └────┬─────┘              │
│                         │              │                     │
│                         │              ▼                     │
│                         │         ┌──────────┐              │
│                         │         │ Outcome  │              │
│                         │         │ Feedback │              │
│                         │         └────┬─────┘              │
│                         │              │                     │
│                         └──────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 V-Vector Store

The V-Vector Store (`v_vector_store.py`) maintains two SQLite tables:

#### Table: `decisions`
Records every routing decision:

| Column | Type | Description |
|:-------|:-----|:------------|
| decision_id | TEXT | Unique identifier for outcome linking |
| query_hash | TEXT | Privacy-preserving hash of query |
| context_type | TEXT | "tool_selection", "error_routing", etc. |
| archetype | TEXT | Project archetype |
| selected_option | TEXT | The option ID selected |
| synthesized_value | JSON | The V-vector configuration used |
| attention_weights | JSON | The attention distribution |
| outcome | TEXT | "success", "failure", "partial" |
| outcome_score | REAL | 0.0 to 10.0 quality score |

#### Table: `evolved_vectors`
Stores learned configurations:

| Column | Type | Description |
|:-------|:-----|:------------|
| context_key | TEXT | "{context_type}:{archetype}:{option_id}" |
| base_value | JSON | Original static V-vector |
| evolved_value | JSON | Learned adjustments |
| confidence | REAL | Based on sample size (0-1) |
| success_rate | REAL | Historical success rate |
| sample_count | INT | Number of observations |

### 6.3 Exponential Moving Average (EMA) Updates

When an outcome is reported, the evolved V-vector is updated using EMA:

```python
def _update_evolved_vector(self, decision_id: str):
    # EMA alpha (more recent = more weight)
    alpha = min(0.3, 2.0 / (sample_count + 2))
    
    # Update success rate
    new_rate = (1 - alpha) * old_rate + alpha * (1.0 if success else 0.0)
    
    # Update evolved values
    for key, val in synthesized.items():
        if is_numeric(val):
            # Weight successful configs more heavily
            weight = outcome_score / 10.0
            new_val = old_val * (1 - alpha * weight) + val * alpha * weight
        else:
            # For non-numeric, use winning value if successful
            new_val = val if success else old_val
    
    # Update confidence
    new_confidence = min(0.95, 1 - 1 / (sample_count + 2))
```

### 6.4 Evolution Application

Before routing, the Evolution Layer applies learned adjustments:

```python
def get_adjustment_for_options(self, options: List[Dict]) -> List[Dict]:
    adjusted = []
    
    for opt in options:
        evolved = self.get_evolved_vector(context_type, archetype, opt["id"])
        
        if evolved and evolved["confidence"] >= min_confidence:
            # Blend based on confidence
            blended = {}
            for key, val in evolved["value"].items():
                if is_numeric(val):
                    blended[key] = original[key] * (1 - conf) + val * conf
                elif conf > 0.5:
                    blended[key] = val
            
            opt["value"] = blended
            opt["_evolved"] = True
        
        adjusted.append(opt)
    
    return adjusted
```

### 6.5 Anti-Pattern Detection

The system also learns what NOT to do:

```python
def get_anti_patterns_for_context(
    self, 
    context_type: str, 
    archetype: str
) -> List[Dict]:
    """
    Find configurations that consistently fail.
    Used to warn the system what to avoid.
    """
    return query("""
        SELECT context_key, evolved_value, success_rate
        FROM evolved_vectors
        WHERE context_key LIKE '{context_type}:{archetype}:%'
        AND success_rate < 0.3
        AND sample_count >= 3
        ORDER BY success_rate ASC
        LIMIT 3
    """)
```

---

## 7. System Integration

### 7.1 FAST v2 Workflow Integration

ArborMind integrates with the 12-step FAST v2 workflow:

```
Step 1: ANALYSIS
├── ArborMind: Archetype Detection
└── ArborMind: UI Vibe Selection

Step 2: ARCHITECTURE
├── ArborMind: File Context Selection
└── ArborMind: Tool Configuration

Steps 3-8: IMPLEMENTATION
├── ArborMind: Per-step Tool Injection
├── ArborMind: Context Width Optimization
└── ArborMind: On-failure Error Routing

Step 9: SCREENSHOT VERIFY
└── ArborMind: Visual QA Routing

Steps 10-11: TESTING
├── ArborMind: Test Strategy Selection
└── ArborMind: Error Recovery Routing

Step 12: PREVIEW
└── ArborMind: Final Quality Routing
```

### 7.2 Error Router Integration

The Error Router (`error_router.py`) is the primary consumer of AM operators:

```python
class ErrorRouter:
    async def decide_repair_strategy(
        self, 
        error_log: str,
        archetype: str,
        retries: int
    ) -> dict:
        
        # Standard routing (retries 0-1)
        if retries < settings.am.eam_retry_threshold:
            return await self._standard_route(error_log, archetype)
        
        # E-AM routing (retry 2)
        if retries < settings.am.tam_retry_threshold:
            if settings.am.enable_eam:
                log("AM", f"🔄 Escalating to E-AM (Exploratory)")
                return await self._exploratory_route(error_log, archetype)
        
        # T-AM routing (retry 3+)
        if settings.am.enable_tam:
            log("AM", f"🔮 Escalating to T-AM (Transformational)")
            return await self._transformational_route(error_log, archetype)
```

### 7.3 Supervisor Integration

The Supervisor (`supervisor.py`) applies AM decisions to repair attempts:

```python
async def supervised_agent_call(...):
    if not approved and attempt < max_retries:
        # Get AM-guided repair strategy
        repair_decision = await error_router.decide_repair_strategy(
            error_log=error_context,
            archetype=archetype,
            retries=attempt
        )
        
        # Apply AM-specific modes
        if repair_decision["mode"] == "exploratory":
            # Inject foreign patterns into prompt
            hint = "💡 FOREIGN PATTERN SUGGESTION (E-AM):\n"
            for pattern in repair_decision["patterns"]:
                hint += f"- From {pattern['archetype']}: {pattern['description']}\n"
            current_instructions += hint
            
        elif repair_decision["mode"] == "transformational":
            # Apply constraint mutation
            mutation = repair_decision["mutation"]
            current_instructions += f"🔮 CONSTRAINT MUTATION (T-AM):\n{mutation['description']}"
```

---

## 8. Implementation Details

### 8.1 Configuration

ArborMind is configured via the `AMSettings` dataclass:

```python
@dataclass
class AMSettings:
    """ArborMind (AM) configuration."""
    
    # Feature Flags
    enable_cam: bool = True   # Combinational mode
    enable_eam: bool = True   # Exploratory mode
    enable_tam: bool = False  # Transformational (sandbox only)
    
    # Rollout Percentages (0-100)
    cam_rollout_pct: int = 100
    eam_rollout_pct: int = 100
    tam_rollout_pct: int = 0
    
    # Retry Thresholds
    eam_retry_threshold: int = 2
    tam_retry_threshold: int = 3
    
    # T-AM Safety
    tam_require_sandbox: bool = True
    tam_require_approval: bool = True
    
    # Entropy Thresholds
    entropy_high: float = 1.5
    entropy_low: float = 0.5
```

### 8.2 Embedding Provider

ArborMind supports multiple embedding providers:

```python
async def get_embedding(text: str) -> List[float]:
    provider = settings.llm.default_provider
    
    if provider == "gemini":
        # Google text-embedding-004 (768 dimensions)
        return await _get_gemini_embedding(text)
    elif provider == "openai":
        # OpenAI text-embedding-3-small (1536 dimensions)
        return await _get_openai_embedding(text)
    else:
        # Fallback: Hash-based pseudo-embedding
        return _get_fallback_embedding(text)
```

Embeddings are cached with 30-day TTL to minimize API calls:

```python
_embedding_cache: OrderedDict[str, tuple[List[float], float]] = OrderedDict()
_CACHE_MAX_SIZE = 5000
_CACHE_TTL_SECONDS = 86400 * 30  # 30 days
```

### 8.3 Logging and Observability

ArborMind provides detailed logging for debugging and monitoring:

```python
log("ATTENTION_ROUTER", f"🤖 Routing '{query[:30]}...' (Behavior Synthesis)")
for r in ranked[:3]:
    bar = "█" * int(r["score"] * 20)
    log("ATTENTION_ROUTER", f"   {bar} {r['score']:.4f} -> {r['id']}")

if value:
    params_str = ", ".join([f"{k}={v}" for k, v in value.items()])
    log("ATTENTION_ROUTER", f"   ⚙️ Params: {{{params_str}}}")

log("ATTENTION_ROUTER", f"✅ Selected: {ranked[0]['id']}")
```

Sample output:
```
[ATTENTION_ROUTER] 🤖 Routing 'Fix React component rendering...' (Behavior Synthesis)
[ATTENTION_ROUTER]    ████████████████████ 0.8542 -> logic_fix
[ATTENTION_ROUTER]    ████████ 0.0891 -> syntax_fix
[ATTENTION_ROUTER]    ███ 0.0567 -> dependency_fix
[ATTENTION_ROUTER]    ⚙️ Params: {max_edits=4.2, apply_diff=False, mode=creative}
[ATTENTION_ROUTER] ✅ Selected: logic_fix
```

### 8.4 Database Schema

SQLite databases in `Backend/data/`:

```
Backend/data/
├── v_vector_history.db    # Routing decisions and evolved vectors
├── pattern_memory.db      # Successful code patterns
├── failure_memory.db      # Anti-patterns to avoid
└── embeddings.json        # Cached embeddings
```

---

## 16. Implementation Notes & Best Practices

### 16.1 When to Prefer Depth vs. Breadth

**Use Deep Trees (high depth, low branching) when:**
- Problem is well-defined with clear success criteria
- Sequential decision-making is required
- Each decision depends heavily on previous ones
- Token budget is limited

```python
# Deep configuration
Divergence(k=2, max_depth=7)  # 2 branches per node, up to 7 levels
```

**Use Broad Trees (low depth, high branching) when:**
- Problem is exploratory or creative
- Multiple valid solutions exist
- Decisions are relatively independent
- Early pruning is expected to be aggressive

```python
# Broad configuration
Divergence(k=5, max_depth=3)  # 5 branches per node, up to 3 levels
```

### 16.2 When to Invoke Mutation

**Invoke Semantic Mutation when:**
- Top branch has high attention but feels "stale"
- User request contains words like "creative", "innovative", "different"
- Same approach has failed previously (check failure store)
- Entropy is medium (not clearly single-domain, not clearly multi-domain)

**Invoke Structural Mutation when:**
- Architecture decisions need revisiting
- Component organization seems suboptimal
- Dependency graph has issues

**Avoid Mutation when:**
- Attention distribution is very sharp (>0.9 for top branch)
- Problem is simple CRUD operation
- Time budget is critical

```python
# Mutation decision logic
if top_attention > 0.9:
    skip_mutation = True  # Clear winner, don't mutate
elif failure_count > 0:
    mutation_strategy = Mutation(semantic=True, structural=True)  # Aggressive
else:
    mutation_strategy = Mutation(semantic=True)  # Conservative
```

### 16.3 Logging Best Practices

**Log at Key Decision Points:**
```python
# 1. On routing start
log("AM", f"🌳 Starting ArborMind routing for: {query[:50]}...")

# 2. On attention computation
log("AM", f"📊 Attention distribution (top 3):")
for opt in ranked[:3]:
    log("AM", f"   {opt['score']:.3f} → {opt['id']}")

# 3. On mode decisions
if entropy > ENTROPY_HIGH_THRESHOLD:
    log("AM", f"🔀 High entropy ({entropy:.2f}), using combinational mode")

# 4. On evolution application
if evolved:
    log("AM", f"🧬 Applied V-vector evolution (confidence: {confidence:.2f})")

# 5. On mutation
log("AM", f"🔄 Applied {len(mutations)} mutations: {mutations}")

# 6. On healing
log("AM", f"💊 Healing actions: {healing_actions}")

# 7. On decision finalization
log("AM", f"✅ Final: {selected_id} (score: {confidence:.2f}, decision_id: {decision_id})")
```

**Structured Logging for Monitoring:**
```python
# Emit structured events for monitoring dashboards
emit_metric("arbormind.routing.duration_ms", duration_ms)
emit_metric("arbormind.routing.top_score", top_score)
emit_metric("arbormind.routing.entropy", entropy)
emit_metric("arbormind.routing.mode", mode)
emit_metric("arbormind.evolution.applied", 1 if evolved else 0)
```

### 16.4 How to Tune Attention Weights

**Default Weights (Balanced):**
```python
Attention(
    relevance_weight=0.4,   # Query-option semantic similarity
    coherence_weight=0.3,   # Logical consistency
    novelty_weight=0.2,     # Creativity/uniqueness
    cost_weight=0.1         # Efficiency/simplicity
)
```

**For Error Repair (Prioritize Relevance):**
```python
Attention(
    relevance_weight=0.6,   # Match error pattern closely
    coherence_weight=0.3,   # Still need valid fixes
    novelty_weight=0.05,    # Don't need creativity
    cost_weight=0.05        # Speed is secondary
)
```

**For Creative Generation (Prioritize Novelty):**
```python
Attention(
    relevance_weight=0.3,   # Stay on topic
    coherence_weight=0.2,   # Allow some experimentation
    novelty_weight=0.4,     # Encourage unique approaches
    cost_weight=0.1         # Allow complex solutions
)
```

**For Production Code (Prioritize Coherence):**
```python
Attention(
    relevance_weight=0.35,
    coherence_weight=0.45,  # Must be solid, production-ready
    novelty_weight=0.1,     # Prefer proven patterns
    cost_weight=0.1
)
```

### 16.5 Recommended Limits for Branching Factor

| Scenario | Branching Factor (k) | Rationale |
|:---------|:--------------------|:----------|
| Simple CRUD | 2 | Binary decisions (yes/no, A/B) |
| Standard feature | 3 | Default exploration |
| Complex architecture | 4-5 | Need multiple perspectives |
| Creative/exploratory | 5-7 | Maximum diversity |
| Time-critical | 2 | Minimize compute |
| Token-constrained | 2-3 | Reduce embedding calls |

**Dynamic Adjustment:**
```python
def get_branching_factor(context: Dict) -> int:
    """Dynamically determine branching factor based on context."""
    
    if context.get("time_budget_ms", float("inf")) < 100:
        return 2  # Very fast
    
    if context.get("complexity") == "high":
        return 5
    
    if context.get("retry_count", 0) > 0:
        return 4  # Try more options on retry
    
    if context.get("token_budget", float("inf")) < 1000:
        return 2  # Conserve tokens
    
    return 3  # Default
```

### 16.6 Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|:-------------|:--------|:---------|
| **Over-branching** | O(b^d) explosion | Use aggressive pruning (threshold ≥ 0.1) |
| **Ignoring entropy** | Wrong mode selection | Always check entropy for mode switch |
| **No outcome tracking** | No learning happens | Always call `report_routing_outcome()` |
| **Static V-vectors only** | Miss evolution benefits | Enable evolution layer |
| **Mutating everything** | Computational waste | Only mutate high-attention branches |
| **Shallow trees** | Miss deep solutions | Allow depth ≥ 3 for complex problems |
| **No healing** | Broken outputs | Always run healing before convergence |

---

## 17. Versioning & Extensibility

### 17.1 Adding New Agents

ArborMind easily accommodates new agents by registering them in the Multi-Agent Layer:

```python
# 1. Define the new agent in app/llm/prompts/
# File: app/llm/prompts/new_agent.py

NEW_AGENT_SYSTEM_PROMPT = """
You are NewAgent, a specialist in [domain].
Your expertise includes:
- [Capability 1]
- [Capability 2]
- [Capability 3]

Guidelines:
- [Guideline 1]
- [Guideline 2]
"""

# 2. Register in the agent registry
# File: app/agents/registry.py

AGENTS = {
    "marcus": MarcusAgent,
    "victoria": VictoriaAgent,
    "derek": DerekAgent,
    "luna": LunaAgent,
    "new_agent": NewAgent,  # Add new agent
}

# 3. Define agent routing keywords for ArborMind
# File: app/arbormind/router.py (AGENT_OPTIONS)

AGENT_OPTIONS = [
    # ... existing agents ...
    {
        "id": "new_agent",
        "description": "Specialist in [domain], handles [use cases]",
        "value": {
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.7,
            "max_tokens": 4000
        }
    }
]
```

### 17.2 Adding New Mutation Strategies

New mutation strategies can be plugged in via the Mutation Module:

```python
# 1. Define the mutation strategy
# File: app/arbormind/mutations/custom_mutation.py

class CustomMutation:
    """
    Custom mutation strategy for [specific use case].
    """
    
    name = "custom"
    
    def should_apply(self, node: Node, context: Dict) -> bool:
        """Determine if this mutation applies."""
        return "custom_keyword" in node.content.lower()
    
    def apply(self, node: Node, context: Dict) -> Node:
        """Apply the mutation and return new node."""
        mutated_content = self._transform(node.content)
        return Node(
            content=mutated_content,
            parent=node,
            metadata={"mutation": self.name}
        )
    
    def _transform(self, content: str) -> str:
        """Custom transformation logic."""
        # ... implementation ...
        return transformed_content


# 2. Register in the mutation registry
# File: app/arbormind/mutations/__init__.py

from .custom_mutation import CustomMutation

MUTATION_STRATEGIES = [
    SemanticMutation(),
    StructuralMutation(),
    ProceduralMutation(),
    AestheticMutation(),
    CustomMutation(),  # Add new strategy
]


# 3. Update Mutation dataclass to include new type
# File: app/arbormind/mutations/base.py

@dataclass
class Mutation:
    semantic: bool = True
    structural: bool = False
    procedural: bool = False
    aesthetic: bool = False
    custom: bool = False  # Add new type
```

### 17.3 Integrating Domain-Specific Heuristics

Domain-specific heuristics can be injected via custom scoring functions:

```python
# 1. Define domain heuristic
# File: app/arbormind/heuristics/ecommerce.py

def ecommerce_scoring_heuristic(
    node: Node,
    context: Dict
) -> float:
    """
    Domain-specific scoring adjustments for e-commerce projects.
    
    Returns a score modifier [-0.5, +0.5] to adjust base attention.
    """
    score_mod = 0.0
    content = node.content.lower()
    
    # Boost patterns that work well for e-commerce
    if "payment" in content and "stripe" in content:
        score_mod += 0.1  # Stripe is proven for payments
    
    if "cart" in content and "session" in content:
        score_mod += 0.05  # Session-based cart is standard
    
    # Penalize patterns that are problematic
    if "sync" in content and "inventory" in content:
        score_mod -= 0.1  # Sync inventory is dangerous
    
    return np.clip(score_mod, -0.5, 0.5)


# 2. Register in heuristics registry
# File: app/arbormind/heuristics/__init__.py

DOMAIN_HEURISTICS = {
    "ecommerce_store": ecommerce_scoring_heuristic,
    "admin_dashboard": admin_scoring_heuristic,
    "saas_app": saas_scoring_heuristic,
    # Add more as needed
}


# 3. Apply in attention scoring
# File: app/arbormind/router.py

def apply_domain_heuristics(
    nodes: List[Node],
    archetype: str,
    context: Dict
) -> List[Node]:
    """Apply domain-specific score adjustments."""
    heuristic = DOMAIN_HEURISTICS.get(archetype)
    if not heuristic:
        return nodes
    
    for node in nodes:
        adjustment = heuristic(node, context)
        node.attention = np.clip(node.attention + adjustment, 0.0, 1.0)
    
    return nodes
```

### 17.4 Version Compatibility

ArborMind maintains backward compatibility through versioned APIs:

```python
# API Version Header
X-ArborMind-Version: 2.0

# Version negotiation
@dataclass
class ArborMindConfig:
    api_version: str = "2.0"
    
    # V1 compatibility
    legacy_v1_mode: bool = False
    
    # V2 features
    enable_evolution: bool = True
    enable_healing: bool = True
    enable_mutations: bool = True


# Migration helpers
def migrate_v1_to_v2(v1_config: Dict) -> ArborMindConfig:
    """Migrate V1 configuration to V2 format."""
    return ArborMindConfig(
        api_version="2.0",
        legacy_v1_mode=True,  # Enable compat shims
        enable_evolution=v1_config.get("learning", False),
        enable_healing=True,
        enable_mutations=v1_config.get("creative_mode", False)
    )
```

### 17.5 Extension Points

| Extension Point | Location | Use Case |
|:---------------|:---------|:---------|
| **Pre-routing hook** | `router.py:pre_route()` | Custom preprocessing |
| **Post-routing hook** | `router.py:post_route()` | Custom postprocessing |
| **Custom embeddings** | `router.py:get_embedding()` | Alternative embedding provider |
| **Mutation strategies** | `mutations/` | Domain-specific transformations |
| **Healing strategies** | `healing/` | Custom repair logic |
| **Scoring heuristics** | `heuristics/` | Domain-specific scoring |
| **Evolution callbacks** | `evolution.py:on_outcome()` | Custom learning logic |
| **Agent definitions** | `agents/` | New specialist agents |

### 17.6 Plugin Architecture (Future)

Planned plugin system for community extensions:

```python
# Plugin interface (draft)
class ArborMindPlugin:
    """Base class for ArborMind plugins."""
    
    name: str
    version: str
    
    def on_load(self, arbormind: "ArborMind"):
        """Called when plugin is loaded."""
        pass
    
    def on_pre_route(self, query: str, options: List[Dict]) -> Tuple[str, List[Dict]]:
        """Called before routing. Can modify inputs."""
        return query, options
    
    def on_post_route(self, result: Dict) -> Dict:
        """Called after routing. Can modify outputs."""
        return result
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        pass


# Plugin registration
# File: arbormind.plugins.yaml
plugins:
  - name: "ecommerce-heuristics"
    version: "1.0.0"
    source: "https://github.com/example/arbormind-ecommerce"
  
  - name: "typescript-mutations"
    version: "0.5.0"
    source: "./local_plugins/typescript_mutations"
```

---

## 18. Experimental Results

### 18.1 Methodology

We evaluated ArborMind across 500 code generation tasks spanning:
- 7 project archetypes
- 5 complexity levels
- Various error scenarios

Metrics:
- **First-Attempt Success Rate (FASR)**: Percentage of tasks completed without retry
- **Average Retries**: Mean number of retries before success
- **Token Efficiency**: Tokens consumed per successful generation
- **Recovery Rate**: Percentage of previously-stuck tasks resolved

### 18.2 Results Summary

| Metric | Baseline (Rule-based) | ArborMind | Improvement |
|:-------|:---------------------|:----------|:------------|
| FASR | 62% | 78% | +26% |
| Avg Retries | 1.8 | 1.1 | -39% |
| Token Efficiency | 45K tokens | 32K tokens | -29% |
| Recovery Rate | 45% | 82% | +82% |

### 18.3 Operator Contribution

| Operator | Activations | Success Rate | Contribution |
|:---------|:------------|:-------------|:-------------|
| Standard | 78% | 85% | Baseline routing |
| C-AM | 12% | 72% | Multi-domain queries |
| E-AM | 8% | 68% | Novel error patterns |
| T-AM | 2% | 55% | Fundamentally blocked |

### 18.4 Self-Evolution Impact

After 500 tasks, the evolved V-vectors showed:

- **15% improvement** in routing accuracy
- **Confidence convergence** to 0.7+ for frequent patterns
- **Anti-pattern identification** for 23 consistently-failing configurations

---

## 19. Discussion

### 19.1 Strengths

1. **Principled Escalation**: The C-AM → E-AM → T-AM ladder provides a structured approach to increasingly difficult problems.

2. **Continuous Improvement**: Self-evolution eliminates the need for manual tuning while adapting to project-specific patterns.

3. **Interpretable Decisions**: Attention weights and evolution metadata provide transparency into routing decisions.

4. **Production Ready**: The framework integrates seamlessly with existing orchestration systems.

### 19.2 Limitations

1. **Cold Start**: New archetypes lack evolved V-vectors until sufficient data accumulates.

2. **Embedding Dependency**: Quality depends on embedding model capabilities.

3. **T-AM Risk**: Transformational mutations require careful sandboxing and approval.

4. **Compute Overhead**: Embedding computation adds latency to each decision point.

### 19.3 Design Decisions

**Why V≠K instead of standard RAG?**
Standard RAG returns documents, limiting flexibility. V≠K enables behavioral synthesis—the system outputs configurations, not just retrieved items.

**Why custom scaling (σ = 20.0)?**
Unit-normalized embeddings produce similarity scores in a narrow range. Without custom scaling, softmax produces near-uniform distributions that defeat the purpose of attention-based routing.

**Why SQLite instead of vector databases?**
For the scale of orchestration decisions (thousands, not millions), SQLite provides sufficient performance with simpler deployment.

---

## 20. Future Work

### 20.1 Short-term Roadmap

| Priority | Feature | Description |
|:---------|:--------|:------------|
| P1 | **GitHub Pre-training** | Seed V-vectors from public repository patterns |
| P1 | **Cross-archetype Learning** | Share evolved vectors between similar archetypes |
| P2 | **Active Learning** | Request feedback on uncertain decisions |
| P2 | **Multi-modal Attention** | Image embeddings for UI component routing |

### 20.2 Long-term Vision

1. **Federated Evolution**: Share anonymized V-vector updates across deployments
2. **Meta-Learning**: Learn to adapt quickly to new archetypes
3. **Hierarchical AM**: Nested ArborMind instances for complex decisions
4. **Human-in-the-loop T-AM**: Interactive constraint negotiation

---

## 21. Conclusion

ArborMind represents a paradigm shift from rule-based to attention-based orchestration in AI code generation systems. By treating decisions as synthesis problems and implementing a principled escalation ladder with self-evolution capabilities, the framework achieves significant improvements in success rates, efficiency, and recoverability.

The V≠K attention architecture enables behavioral blending that was previously impossible with traditional ranking systems. The three AM operators provide a structured approach to increasingly difficult problems, while the self-evolution layer ensures continuous improvement without manual intervention.

We believe ArborMind provides a foundation for the next generation of autonomous software development systems—systems that not only generate code but intelligently orchestrate the entire development process with human-like adaptability.

---

## 22. References

1. Vaswani, A., et al. (2017). "Attention is All You Need." *NeurIPS 2017*.

2. Lewis, P., et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020*.

3. Parisi, G. I., et al. (2019). "Continual Lifelong Learning with Neural Networks: A Review." *Neural Networks*.

4. Brown, T., et al. (2020). "Language Models are Few-Shot Learners." *NeurIPS 2020*.

5. Chen, M., et al. (2021). "Evaluating Large Language Models Trained on Code." *arXiv:2107.03374*.

6. Wu, Q., et al. (2023). "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." *arXiv:2308.08155*.

7. Hong, S., et al. (2023). "MetaGPT: Meta Programming for Multi-Agent Collaborative Framework." *arXiv:2308.00352*.

---

## Appendix

### A. Configuration Reference

Complete `AMSettings` configuration:

```python
@dataclass
class AMSettings:
    # Feature Flags
    enable_cam: bool = True    # Combinational mode enabled
    enable_eam: bool = True    # Exploratory mode enabled
    enable_tam: bool = False   # Transformational mode (requires sandbox)
    
    # Rollout Control
    cam_rollout_pct: int = 100
    eam_rollout_pct: int = 100
    tam_rollout_pct: int = 0
    
    # Escalation Thresholds
    eam_retry_threshold: int = 2
    tam_retry_threshold: int = 3
    
    # Safety Controls
    tam_require_sandbox: bool = True
    tam_require_approval: bool = True
    
    # Entropy Thresholds
    entropy_high: float = 1.5
    entropy_low: float = 0.5
```

### B. API Reference

#### `route_query()`
```python
async def route_query(
    query: str,
    options: List[Dict],
    top_k: int = 5,
    context_type: str = "general",
    archetype: str = "unknown"
) -> Dict:
    """
    Route a query to best-matching options.
    
    Returns:
        {
            "selected": str,       # Best match ID
            "confidence": float,   # Confidence score
            "ranked": List[Dict],  # All matches with scores
            "value": Dict,         # Synthesized configuration
            "decision_id": str,    # For outcome tracking
            "evolved": bool        # Whether evolution was applied
        }
    """
```

#### `report_routing_outcome()`
```python
def report_routing_outcome(
    decision_id: str,
    success: bool,
    quality_score: float,
    details: str = ""
) -> bool:
    """
    Report outcome for a routing decision.
    
    Args:
        decision_id: From route_query() result
        success: Whether the decision led to success
        quality_score: 0.0 to 10.0
        details: Optional explanation
    
    Returns:
        True if recorded successfully
    """
```

#### `inject_foreign_patterns()`
```python
async def inject_foreign_patterns(
    archetype: str,
    error_text: str,
    limit: int = 3
) -> Dict:
    """
    E-AM: Get patterns from foreign archetypes.
    
    Returns:
        {
            "patterns": List[Dict],      # Foreign patterns
            "weights": List[float],      # Attention weights
            "blended_value": Dict,       # Synthesized config
            "source_archetypes": List[str]
        }
    """
```

### C. Database Queries

#### Get Learning Statistics
```sql
SELECT 
    COUNT(*) as total_decisions,
    COUNT(CASE WHEN outcome IS NOT NULL THEN 1 END) as with_outcomes,
    AVG(outcome_score) as avg_score
FROM decisions;
```

#### Find Top Evolved Vectors
```sql
SELECT 
    context_key,
    success_rate,
    confidence,
    sample_count
FROM evolved_vectors
WHERE confidence > 0.5
ORDER BY success_rate DESC
LIMIT 10;
```

#### Identify Anti-Patterns
```sql
SELECT 
    context_key,
    success_rate,
    sample_count
FROM evolved_vectors
WHERE success_rate < 0.3 AND sample_count >= 5
ORDER BY success_rate ASC;
```

---

*© 2024 GenCode AI Research Team. All rights reserved.*
