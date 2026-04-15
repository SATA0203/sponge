"""
Workflow Configuration Module - YAML-based workflow definition

Supports:
- Workflow definition via YAML configuration
- Dynamic workflow graph building
- Runtime workflow switching
- Multiple workflow variants (fast, thorough, custom)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path
from loguru import logger

from langgraph.graph import StateGraph, END


class NodeType(str, Enum):
    """Types of workflow nodes"""
    PLANNER = "planner"
    CODER = "coder"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    TESTER = "tester"


class EdgeType(str, Enum):
    """Types of edges"""
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


@dataclass
class NodeConfig:
    """Configuration for a workflow node"""
    node_type: NodeType
    name: str
    timeout: int = 300
    retries: int = 3
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeConfig:
    """Configuration for a workflow edge"""
    source: str
    target: str | List[str]
    edge_type: EdgeType = EdgeType.SEQUENTIAL
    condition: Optional[str] = None  # Condition function name for conditional edges


@dataclass
class WorkflowConfig:
    """Complete workflow configuration"""
    name: str
    description: str
    version: str = "1.0.0"
    nodes: List[NodeConfig] = field(default_factory=list)
    edges: List[EdgeConfig] = field(default_factory=list)
    entry_point: str = "planner"
    max_iterations: int = 3
    enable_checkpointing: bool = True
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "WorkflowConfig":
        """Load workflow configuration from YAML file"""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow config not found: {yaml_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowConfig":
        """Create workflow configuration from dictionary"""
        nodes = [
            NodeConfig(
                node_type=NodeType(node['type']),
                name=node['name'],
                timeout=node.get('timeout', 300),
                retries=node.get('retries', 3),
                params=node.get('params', {}),
            )
            for node in data.get('nodes', [])
        ]
        
        edges = []
        for edge_data in data.get('edges', []):
            edge_type = EdgeType(edge_data.get('type', 'sequential'))
            
            # Handle conditional edges with multiple targets
            if edge_type == EdgeType.CONDITIONAL:
                target = edge_data.get('targets', [])
                condition = edge_data.get('condition')
            else:
                target = edge_data.get('target')
                condition = None
            
            edges.append(
                EdgeConfig(
                    source=edge_data['source'],
                    target=target,
                    edge_type=edge_type,
                    condition=condition,
                )
            )
        
        return cls(
            name=data.get('name', 'unnamed_workflow'),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            nodes=nodes,
            edges=edges,
            entry_point=data.get('entry_point', 'planner'),
            max_iterations=data.get('max_iterations', 3),
            enable_checkpointing=data.get('enable_checkpointing', True),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow configuration to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'nodes': [
                {
                    'type': node.node_type.value,
                    'name': node.name,
                    'timeout': node.timeout,
                    'retries': node.retries,
                    'params': node.params,
                }
                for node in self.nodes
            ],
            'edges': [
                {
                    'source': edge.source,
                    'target': edge.target if isinstance(edge.target, str) else None,
                    'targets': edge.target if isinstance(edge.target, list) else None,
                    'type': edge.edge_type.value,
                    'condition': edge.condition,
                }
                for edge in self.edges
            ],
            'entry_point': self.entry_point,
            'max_iterations': self.max_iterations,
            'enable_checkpointing': self.enable_checkpointing,
        }
    
    def to_yaml(self, output_path: str):
        """Save workflow configuration to YAML file"""
        with open(output_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved workflow config to {output_path}")


# Predefined workflow configurations

def get_fast_workflow() -> WorkflowConfig:
    """Get a fast workflow configuration (minimal checks)"""
    return WorkflowConfig(
        name="fast_workflow",
        description="Fast workflow with minimal validation",
        version="1.0.0",
        nodes=[
            NodeConfig(NodeType.PLANNER, "planner"),
            NodeConfig(NodeType.CODER, "coder"),
            NodeConfig(NodeType.EXECUTOR, "executor"),
            NodeConfig(NodeType.REVIEWER, "reviewer"),
        ],
        edges=[
            EdgeConfig("planner", "coder"),
            EdgeConfig("coder", "executor"),
            EdgeConfig("executor", "reviewer"),
            EdgeConfig(
                "reviewer",
                ["coder", END],
                EdgeType.CONDITIONAL,
                condition="_should_continue",
            ),
        ],
        max_iterations=2,
    )


def get_thorough_workflow() -> WorkflowConfig:
    """Get a thorough workflow configuration (with testing)"""
    return WorkflowConfig(
        name="thorough_workflow",
        description="Thorough workflow with comprehensive testing",
        version="1.0.0",
        nodes=[
            NodeConfig(NodeType.PLANNER, "planner"),
            NodeConfig(NodeType.CODER, "coder"),
            NodeConfig(NodeType.EXECUTOR, "executor"),
            NodeConfig(NodeType.REVIEWER, "reviewer"),
            NodeConfig(NodeType.TESTER, "tester", timeout=600),
        ],
        edges=[
            EdgeConfig("planner", "coder"),
            EdgeConfig("coder", "executor"),
            EdgeConfig("executor", "reviewer"),
            EdgeConfig("reviewer", "tester"),
            EdgeConfig(
                "tester",
                ["coder", END],
                EdgeType.CONDITIONAL,
                condition="_should_continue",
            ),
        ],
        max_iterations=5,
    )


def get_standard_workflow() -> WorkflowConfig:
    """Get the standard workflow configuration"""
    return WorkflowConfig(
        name="standard_workflow",
        description="Standard workflow with balanced checks",
        version="1.0.0",
        nodes=[
            NodeConfig(NodeType.PLANNER, "planner"),
            NodeConfig(NodeType.CODER, "coder"),
            NodeConfig(NodeType.EXECUTOR, "executor"),
            NodeConfig(NodeType.REVIEWER, "reviewer"),
            NodeConfig(NodeType.TESTER, "tester"),
        ],
        edges=[
            EdgeConfig("planner", "coder"),
            EdgeConfig("coder", "executor"),
            EdgeConfig("executor", "reviewer"),
            EdgeConfig("reviewer", "tester"),
            EdgeConfig(
                "tester",
                ["coder", END],
                EdgeType.CONDITIONAL,
                condition="_should_continue",
            ),
        ],
        max_iterations=3,
    )


class WorkflowConfigManager:
    """Manager for workflow configurations"""
    
    _instance: Optional["WorkflowConfigManager"] = None
    _configs: Dict[str, WorkflowConfig] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            # Register default workflows
            self.register_config("standard", get_standard_workflow())
            self.register_config("fast", get_fast_workflow())
            self.register_config("thorough", get_thorough_workflow())
            logger.info("Initialized WorkflowConfigManager with default configs")
    
    def register_config(self, config_id: str, config: WorkflowConfig):
        """Register a workflow configuration"""
        self._configs[config_id] = config
        logger.info(f"Registered workflow config: {config_id} ({config.name})")
    
    def load_config_from_yaml(self, config_id: str, yaml_path: str):
        """Load and register a workflow configuration from YAML"""
        config = WorkflowConfig.from_yaml(yaml_path)
        self.register_config(config_id, config)
    
    def get_config(self, config_id: str) -> WorkflowConfig:
        """Get a workflow configuration by ID"""
        if config_id not in self._configs:
            raise ValueError(f"Unknown workflow config: {config_id}")
        return self._configs[config_id]
    
    def list_configs(self) -> List[str]:
        """List all registered workflow configuration IDs"""
        return list(self._configs.keys())
    
    def remove_config(self, config_id: str):
        """Remove a workflow configuration"""
        if config_id in self._configs:
            del self._configs[config_id]
            logger.info(f"Removed workflow config: {config_id}")
        else:
            logger.warning(f"Cannot remove unknown workflow config: {config_id}")


# Global config manager instance
_config_manager: Optional[WorkflowConfigManager] = None


def get_workflow_config_manager() -> WorkflowConfigManager:
    """Get or create the global workflow config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = WorkflowConfigManager()
    return _config_manager


# Example YAML template
WORKFLOW_YAML_TEMPLATE = """
name: custom_workflow
description: Custom workflow configuration
version: 1.0.0

nodes:
  - type: planner
    name: planner
    timeout: 300
    retries: 3
    params:
      temperature: 0.7
  
  - type: coder
    name: coder
    timeout: 600
    retries: 3
    params:
      temperature: 0.5
  
  - type: executor
    name: executor
    timeout: 300
    retries: 2
  
  - type: reviewer
    name: reviewer
    timeout: 300
    retries: 2
    params:
      strict_mode: true
  
  - type: tester
    name: tester
    timeout: 600
    retries: 2

edges:
  - source: planner
    target: coder
    type: sequential
  
  - source: coder
    target: executor
    type: sequential
  
  - source: executor
    target: reviewer
    type: sequential
  
  - source: reviewer
    target: tester
    type: sequential
  
  - source: tester
    targets: [coder, end]
    type: conditional
    condition: _should_continue

entry_point: planner
max_iterations: 3
enable_checkpointing: true
"""
