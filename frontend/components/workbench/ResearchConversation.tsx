import { AlertTriangle, Bot, CheckCircle2, RotateCcw, UserRound } from "lucide-react";

import { ResearchRun, RunStepAction } from "../../lib/api";
import { buildConversationMessages, stepActions } from "../../lib/workbench";


export function ResearchConversation({
  run,
  busy,
  onStepAction,
}: {
  run: ResearchRun | null;
  busy: boolean;
  onStepAction: (stepName: string, action: RunStepAction) => void;
}) {
  if (!run) {
    return (
      <section className="conversation-log empty-conversation">
        <Bot size={18} />
        <p>输入科研问题后直接启动。执行进度、自动重试和需要处理的问题会显示在这里。</p>
      </section>
    );
  }

  const messages = buildConversationMessages(run);
  return (
    <section className="conversation-log" aria-label="科研执行对话">
      {messages.map((message) => {
        const step = message.stepName
          ? [...run.steps].reverse().find((item) => item.name === message.stepName)
          : undefined;
        const actions = step ? stepActions(step) : [];
        return (
          <article className={`conversation-message ${message.kind}`} key={message.id}>
            <div className="message-icon">
              {message.kind === "user" ? <UserRound size={15} /> : message.kind === "success" ? <CheckCircle2 size={15} /> : message.kind === "error" || message.kind === "warning" ? <AlertTriangle size={15} /> : <Bot size={15} />}
            </div>
            <div className="message-body">
              <strong>{message.title}</strong>
              <p>{message.text}</p>
              {step?.attempts ? <small>已尝试 {step.attempts} 次</small> : null}
              {actions.length > 0 && message.stepName && (
                <div className="message-actions">
                  {actions.map((action) => (
                    <button
                      className={action === "retry" ? "secondary" : "ghost-button"}
                      disabled={busy}
                      key={action}
                      onClick={() => onStepAction(message.stepName!, action)}
                      type="button"
                    >
                      <RotateCcw size={13} />
                      {action === "retry" ? "重新执行" : "跳过"}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </article>
        );
      })}
    </section>
  );
}
