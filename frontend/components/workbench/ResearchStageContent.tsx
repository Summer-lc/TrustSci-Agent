import { ReactNode } from "react";

import { WorkbenchStageId } from "../../lib/workbench";


export function ResearchStageContent({
  activeStage,
  sections,
}: {
  activeStage: WorkbenchStageId;
  sections: Record<WorkbenchStageId, ReactNode>;
}) {
  return (
    <section className="stage-content" aria-live="polite">
      {sections[activeStage]}
    </section>
  );
}
