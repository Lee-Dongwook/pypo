from typing import TYPE_CHECKING

from langgraph.graph import END

if TYPE_CHECKING:
    from ..schemas import AgentWorkflow

END_TARGETS = {"end", "END", str(END)}

def compute_producers(workflow: "AgentWorkflow") -> dict[str, list[str]]:
    producers: dict[str, list[str]] = {}

    for node in workflow.nodes:
        action = node.action
        output_key = getattr(action, "output_key", None)
        if output_key:
            producers.setdefault(output_key, []).append(node.name)
        
        for target in getattr(action, "output_mapping", None) or {}:
            producers.setdefault(target, []).append(node.name)
    return producers

def is_mutually_exclusive(a: str, b: str, conditional_targets: dict[str, set[str]], dominators: dict[str, set[str]]) -> bool:
    for source, targets in conditional_targets.items():
        if source not in dominators.get(a,()) or source not in dominators.get(b, ()):
            continue
        for t1 in targets:
            for t2 in targets:
                if t1 != t2 and t1 in dominators.get(a, ()) and t2 in dominators.get(b, ()):
                    return True
    return False

def compute_dominators(workflow: "AgentWorkflow") -> dict[str, set[str]]:
    names = {node.name for node in workflow.nodes}
    predecessors: dict[str, set[str]] = {}
    for edge in workflow.edges:
        if edge.edge_type == "end" or edge.target in END_TARGETS:
            continue
        if edge.target not in names or edge.source not in names:
            continue
        predecessors.setdefault(edge.target, set()).add(edge.source)
    
    start = workflow.start_node
    dominators = {name: ({name} if name == start else set(names)) for name in names}
    changed = True
    while changed:
        for name in names:
            if name == start:
                continue
            prevs = predecessors.get(name, set())
            currs = (set.intersection(*(dominators[p] for p in prevs)) | {name}) if prevs else {name}
            if currs != dominators[name]:
                dominators[name] = currs
                changed = True
    return dominators

def compute_reachability(workflow: "AgentWorkflow") -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in workflow.edges:
        if edge.edge_type == "end" or edge.target in END_TARGETS:
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)

    reachable: dict[str, set[str]] = {}
    for start in {node.name for node in workflow.nodes}:
        seen: set[str] = set()
        stack = list(adjacency.get(start, ()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency.get(current, ()))
        reachable[start] = seen
    return reachable

def dead_end_nodes(workflow: "AgentWorkflow") -> list[str]:
    sources = {edge.source for edge in workflow.edges}
    return [node.name for node in workflow.nodes if node.name not in sources]

def reachable_from_start(workflow: "AgentWorkflow") -> set[str]:
    adjacency: dict[str, set[str]] = {}
    for edge in workflow.edges:
        if edge.edge_type == "end" or edge.target in END_TARGETS:
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)

    seen: set[str] = set()
    stack = [workflow.start_node]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(adjacency.get(current, ()))
    return seen

def nodes_ending_a_path(workflow: "AgentWorkflow") -> set[str]:
    routers = {edge.source for edge in workflow.edges if edge.edge_type == "conditional"}
    ending = set(dead_end_nodes(workflow))
    ending.update(
        edge.source
        for edge in workflow.edges
        if edge.source not in routers and (edge.edge_type == "end" or edge.target in END_TARGETS)
    )
    return ending
