/** A model-independent change proposal returned by a future AI provider. */
export type ProposedChange = {
  blockId: string
  originalText: string
  replacementText: string
  rationale: string
}

export type ProposalRequest = {
  instruction: string
  selectedText: string
  document: Record<string, unknown>
  jobDescription?: string
}

export interface AssistantProvider {
  proposeChanges(request: ProposalRequest): Promise<ProposedChange[]>
}

// TODO(ai-provider): Implement Ollama and hosted-provider adapters on the API.
// The client must receive structured proposals and require explicit approval;
// model output must never write directly to a CV document.
