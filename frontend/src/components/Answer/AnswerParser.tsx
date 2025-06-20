import { cloneDeep } from 'lodash'

import { AskResponse, Citation } from '../../api'

export type ParsedAnswer = {
  citations: Citation[]
  markdownFormatText: string,
  generated_chart: string | null
} | null

export const enumerateCitations = (citations: Citation[]) => {
  const filepathMap = new Map()
  for (const citation of citations) {
    const { filepath } = citation
    let part_i = 1
    if (filepathMap.has(filepath)) {
      part_i = filepathMap.get(filepath) + 1
    }
    filepathMap.set(filepath, part_i)
    citation.part_index = part_i
  }
  return citations
}

// Return the raw answer and pre-supplied citations without additional parsing or reindexing.
export function parseAnswer(answer: AskResponse): ParsedAnswer {
    if (typeof answer.answer !== "string") return null;
  return {
    citations: answer.citations || [],
    markdownFormatText: answer.answer,
    generated_chart: answer.generated_chart
  }
}
