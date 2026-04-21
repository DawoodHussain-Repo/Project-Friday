export type FridayEventType =
  | "user"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "final";

export interface FridayEvent {
  type: FridayEventType;
  content: string;
}

export interface WorkspaceNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: WorkspaceNode[];
}

export async function getWorkspaceTree(): Promise<WorkspaceNode[]> {
  const response = await fetch("/api/friday", { method: "GET" });
  if (!response.ok) {
    throw new Error("Failed to fetch workspace tree");
  }

  const data = (await response.json()) as { tree: WorkspaceNode[] };
  return data.tree;
}
