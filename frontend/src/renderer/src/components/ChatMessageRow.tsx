/**
 * One message: author, time, body with mention chips, and a delete action for what you can remove.
 *
 * Pressing a chip is what ties chat to the rest of the app: a document opens the project graph at
 * that file, a folder opens it at that folder, and a ticket opens the tickets screen on it.
 */

import type { ChatMention, ChatMessage } from '@shared/types'

import { mentionIcon, mentionOpenHint, mentionText, segmentsOf } from '../lib/chat'
import { initials, relativeTime } from '../lib/tickets'

export function ChatMessageRow({
  message,
  mine,
  canDelete,
  onOpenMention,
  onDelete
}: {
  message: ChatMessage
  mine: boolean
  canDelete: boolean
  onOpenMention: (mention: ChatMention) => void
  onDelete: (messageId: string) => void
}) {
  const author = message.author?.display_name ?? 'Someone'
  const segments = segmentsOf(message)

  return (
    <article className={`chat-msg${mine ? ' chat-msg--mine' : ''}`}>
      <span className="avatar avatar--sm" aria-hidden="true">
        {initials(author)}
      </span>

      <div className="chat-msg__body">
        <div className="chat-msg__meta">
          <span className="chat-msg__author">{author}</span>
          <span className="chat-msg__time">{relativeTime(message.created_at)}</span>
          {canDelete && !message.deleted ? (
            <button
              type="button"
              className="chat-msg__delete btn btn--ghost btn--sm"
              onClick={() => onDelete(message.id)}
              title="Remove this message"
            >
              Delete
            </button>
          ) : null}
        </div>

        {message.deleted ? (
          <p className="chat-msg__text chat-msg__text--deleted">This message was removed.</p>
        ) : (
          <p className="chat-msg__text">
            {segments.map((segment, index) =>
              segment.kind === 'text' ? (
                <span key={`t-${index}`}>{segment.text}</span>
              ) : (
                <button
                  key={`m-${segment.mention.kind}-${segment.mention.id}-${index}`}
                  type="button"
                  className={`mention-chip mention-chip--${segment.mention.kind}`}
                  onClick={() => onOpenMention(segment.mention)}
                  title={mentionOpenHint(segment.mention.kind)}
                >
                  <span aria-hidden="true">{mentionIcon(segment.mention.kind)}</span>
                  {mentionText(segment.mention)}
                </button>
              )
            )}
          </p>
        )}
      </div>
    </article>
  )
}
