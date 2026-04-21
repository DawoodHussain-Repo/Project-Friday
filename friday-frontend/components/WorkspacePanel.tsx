import type { WorkspaceNode } from "../lib/api";

interface WorkspacePanelProps {
  nodes: WorkspaceNode[];
}

function TreeNode({ node }: { node: WorkspaceNode }) {
  if (node.type === "file") {
    return <li className="truncate text-xs text-friday-muted">{node.name}</li>;
  }

  return (
    <li className="truncate text-xs text-friday-muted">
      {node.name}/
      {node.children && node.children.length > 0 ? (
        <ul className="mt-1 list-none space-y-1 pl-4">
          {node.children.map((child) => (
            <TreeNode key={child.path} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function WorkspacePanel({ nodes }: WorkspacePanelProps) {
  return (
    <aside className="chat-scrollbar min-h-[32vh] overflow-auto rounded-2xl border border-friday-line bg-friday-paper p-4 shadow-panel lg:min-h-[82vh]">
      <h3 className="mb-3 font-heading text-lg text-friday-ink">Workspace</h3>
      {nodes.length === 0 ? (
        <p className="text-sm text-friday-muted">
          No files yet in sandbox workspace.
        </p>
      ) : (
        <ul className="list-none space-y-1 pl-1 font-mono">
          {nodes.map((node) => (
            <TreeNode key={node.path} node={node} />
          ))}
        </ul>
      )}
    </aside>
  );
}
