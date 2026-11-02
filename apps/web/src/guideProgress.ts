export interface GuideProgress {
  step: number
  completed: boolean
}

export function guideStorageKey(workspaceId: string) {
  return `dayloom.guide.v3:${workspaceId}`
}

export function readGuideProgress(workspaceId: string): GuideProgress | null {
  try {
    const stored = JSON.parse(localStorage.getItem(guideStorageKey(workspaceId)) ?? 'null')
    if (!stored || typeof stored !== 'object') return null
    return {
      step: Number.isInteger(stored.step) && stored.step >= 0 && stored.step <= 4 ? stored.step : 0,
      completed: stored.completed === true,
    }
  } catch {
    return null
  }
}

export function saveGuideProgress(workspaceId: string, progress: GuideProgress) {
  try {
    localStorage.setItem(
      guideStorageKey(workspaceId),
      JSON.stringify({ step: progress.step, completed: progress.completed }),
    )
    return true
  } catch {
    return false
  }
}
