/**
 * The chat page: a project's group chat on the left, its messages and composer on the right.
 *
 * A project is its chat — there is nothing to create — so the channel list is just "my projects",
 * ordered by the last thing said. Typing `@` offers that project's documents, folders and tickets;
 * pressing a chip opens the graph at that file/folder, or the tickets screen at that ticket.
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import type { ChatMention, ChatChannel, Member } from '@shared/types'

import { dayLabel, groupByDay, messagePreview } from '../lib/chat'
import { describeError } from '../lib/errors'
import { focusFromMention, type GraphFocus } from '../lib/graphFocus'
import { initials, relativeTime } from '../lib/tickets'
import { useChat } from '../state/useChat'
import { useChatChannels } from '../state/useChatChannels'
import { ChatMessageRow } from './ChatMessageRow'
import { MentionTextarea } from './MentionTextarea'
import { Empty, ErrorBox, Spinner } from './primitives'

export function ChatScreen({
  member,
  initialProjectId,
  initialDraft,
  onOpenProject,
  onOpenTicket,
  onOpenCalendar,
  notify
}: {
  member: Member
  /** A chat mention elsewhere asked for this project's chat. */
  initialProjectId?: string | null
  /** A pre-filled message another screen started (a calendar event or a ticket). */
  initialDraft?: string | null
  onOpenProject: (projectId: string, focus: GraphFocus) => void
  onOpenTicket: (projectId: string, ticketId: string) => void
  onOpenCalendar: (projectId: string, eventId: string, eventDay: string | null) => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const { channels, loading: channelsLoading, error: channelsError, reload: reloadChannels } =
    useChatChannels()
  const [selectedId, setSelectedId] = useState<string | null>(initialProjectId ?? null)
  const [text, setText] = useState(initialDraft ?? '')
  const [focusKey, setFocusKey] = useState(0)
  const listRef = useRef<HTMLDivElement | null>(null)

  const selected = useMemo(
    () => channels.find((channel) => channel.project_id === selectedId) ?? null,
    [channels, selectedId]
  )
  const projectId = selected?.project_id ?? null
  const chat = useChat(projectId)

  useEffect(() => {
    if (initialProjectId) setSelectedId(initialProjectId)
  }, [initialProjectId])

  useEffect(() => {
    if (selectedId) return
    if (channels.length > 0) setSelectedId(channels[0].project_id)
  }, [channels, selectedId])

  // A screen that starts a message (a calendar event, a ticket) hands us its draft here: fill the
  // composer and put the caret at the end so the next keystroke continues the sentence.
  useEffect(() => {
    setText(initialDraft ?? '')
    setFocusKey((value) => value + 1)
  }, [initialDraft, initialProjectId])

  useEffect(() => {
    if (chat.error) notify(describeError(chat.error), 'error')
  }, [chat.error, notify])

  useEffect(() => {
    const node = listRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [chat.messages.length, selectedId])

  const days = useMemo(() => groupByDay(chat.messages), [chat.messages])

  const submit = async (): Promise<void> => {
    const body = text.trim()
    if (!body || chat.sending || !projectId) return
    const ok = await chat.send(body)
    if (ok) {
      setText('')
      void reloadChannels()
    }
  }

  const openMention = (item: ChatMention): void => {
    if (!projectId) return
    const focus = focusFromMention(item)
    if (focus) {
      onOpenProject(projectId, focus)
      return
    }
    if (item.kind === 'ticket') onOpenTicket(projectId, item.id)
    if (item.kind === 'event') onOpenCalendar(projectId, item.id, item.event_day)
  }

  const remove = async (messageId: string): Promise<void> => {
    if (!window.confirm('Remove this message? Everyone will see it as removed.')) return
    const ok = await chat.remove(messageId)
    if (ok) void reloadChannels()
  }

  return (
    <div className="screen screen--wide">
      <div className="screen__inner">
        <header className="screen__head">
          <div>
            <h1 className="screen__title">Chat</h1>
            <p className="screen__lede">
              One group chat per project, for everyone who can see it. Type <strong>@</strong> to
              point at a document, a folder, a ticket or a calendar event — pressing the chip opens
              it.
            </p>
          </div>
          <div className="screen__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                void reloadChannels()
                void chat.reload()
              }}
            >
              Refresh
            </button>
          </div>
        </header>

        {channelsLoading ? (
          <div className="empty">
            <Spinner label="Opening your chats" />
          </div>
        ) : null}

        {!channelsLoading && channelsError ? (
          <ErrorBox title="Your chats could not be loaded" detail={describeError(channelsError)}>
            <div style={{ marginTop: 10 }}>
              <button type="button" className="btn btn--sm" onClick={() => void reloadChannels()}>
                Try again
              </button>
            </div>
          </ErrorBox>
        ) : null}

        {!channelsLoading && !channelsError && channels.length === 0 ? (
          <Empty
            title="No project chats yet"
            text="A chat belongs to a project, and a project is created with an upload. Once you have one, its chat is already here."
          />
        ) : null}

        {channels.length > 0 ? (
          <div className="chat">
            <aside className="chat__channels">
              <span className="side__label">Project chats</span>
              <ul className="chat-channel-list">
                {channels.map((channel: ChatChannel) => (
                  <li key={channel.project_id}>
                    <button
                      type="button"
                      className={`chat-channel${
                        channel.project_id === projectId ? ' chat-channel--active' : ''
                      }`}
                      onClick={() => {
                        setSelectedId(channel.project_id)
                        setText('')
                      }}
                    >
                      <span className="avatar avatar--sm" aria-hidden="true">
                        {initials(channel.project_name)}
                      </span>
                      <span className="chat-channel__body">
                        <span className="chat-channel__name">{channel.project_name}</span>
                        <span className="chat-channel__preview">
                          {messagePreview(channel.last_message)}
                        </span>
                      </span>
                      <span className="chat-channel__time">
                        {relativeTime(channel.last_activity_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </aside>

            <section className="chat__main">
              <header className="chat__head">
                <span className="chat__title">{selected?.project_name ?? 'Chat'}</span>
                <span className="chat__hint">
                  Everyone in this project sees this chat. Type @ to mention a document, folder,
                  ticket or calendar event.
                </span>
              </header>

              <div className="chat__messages" ref={listRef}>
                {chat.status === 'loading' ? <Spinner label="Loading messages" /> : null}

                {chat.status === 'error' && chat.error ? (
                  <ErrorBox
                    title="This chat could not be loaded"
                    detail={describeError(chat.error)}
                  >
                    <div style={{ marginTop: 10 }}>
                      <button
                        type="button"
                        className="btn btn--sm"
                        onClick={() => void chat.reload()}
                      >
                        Try again
                      </button>
                    </div>
                  </ErrorBox>
                ) : null}

                {chat.status === 'ready' && chat.messages.length === 0 ? (
                  <p className="side__text">
                    No messages yet. Say hello, or mention a document with @.
                  </p>
                ) : null}

                {days.map((day) => (
                  <div key={day.day} className="chat-day">
                    <span className="chat-day__label">{dayLabel(day.day)}</span>
                    {day.messages.map((message) => (
                      <ChatMessageRow
                        key={message.id}
                        message={message}
                        mine={message.author?.id === member.id}
                        canDelete={message.author?.id === member.id}
                        onOpenMention={openMention}
                        onDelete={(messageId) => void remove(messageId)}
                      />
                    ))}
                  </div>
                ))}
              </div>

              <div className="chat-composer">
                <MentionTextarea
                  projectId={projectId}
                  value={text}
                  onChange={(next) => setText(next)}
                  rows={2}
                  maxLength={4_000}
                  className="chat-composer__input"
                  placeholder="Message the project. Type @ to mention a document, folder, ticket or calendar event."
                  pickerTitle="Mention a document, a folder, a ticket or a calendar event"
                  focusKey={focusKey}
                  onSubmit={() => void submit()}
                />

                <div className="chat-composer__foot">
                  <span className="chat-composer__count">{text.length}/4000</span>
                  <span className="chat-composer__hint">Enter sends · Shift+Enter adds a line</span>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => void submit()}
                    disabled={!text.trim() || chat.sending || !projectId}
                  >
                    {chat.sending ? 'Sending…' : 'Send'}
                  </button>
                </div>
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  )
}

