import { useEffect, useRef, useState } from 'react'
import {
  api, deliveryLabels, stateLabels,
  type Assignment, type DeliveryStatus, type EventData,
  type MailResult, type Preview, type SantaEvent, type Verdict,
} from './api'
import { Confirm } from './Confirm'

const tags = ['participant_nom', 'destinataire_nom', 'evenement_nom', 'budget', 'date']

export function Editor({ initial, onChanged, onDirty, onDuplicate, onDeleted }: {
  initial: SantaEvent
  onChanged: (event: SantaEvent) => void
  onDirty: (dirty: boolean) => void
  onDuplicate: (event: SantaEvent) => void
  onDeleted: () => void
}) {
  const [event, setEvent] = useState(initial)
  const [draft, setDraft] = useState(initial.data)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [password, setPassword] = useState('')
  const [statuses, setStatuses] = useState<DeliveryStatus[]>([])
  const [assignments, setAssignments] = useState<Assignment[] | null>(null)
  const [confirmation, setConfirmation] = useState<'draw' | 'reveal' | 'delete' | 'retry' | null>(null)
  const bodyRef = useRef<HTMLTextAreaElement>(null)
  const subjectRef = useRef<HTMLInputElement>(null)
  const [target, setTarget] = useState<'body' | 'subject'>('body')
  const locked = event.state !== 'draft'
  const inFlight = sending || event.state === 'sending'
  const disabled = busy || inFlight
  const path = `/events/${event.id}`

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty || inFlight) event.preventDefault()
    }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, inFlight])

  useEffect(() => {
    if (!locked) return
    let active = true
    const refresh = async () => {
      try {
        const [current, delivery] = await Promise.all([
          api<SantaEvent>(path), api<DeliveryStatus[]>(`${path}/deliveries`),
        ])
        if (active) {
          setEvent(current)
          setStatuses(delivery)
          onChanged(current)
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Lecture du suivi impossible.')
      }
    }
    void refresh()
    const timer = inFlight ? window.setInterval(() => { void refresh() }, 1500) : undefined
    return () => { active = false; window.clearInterval(timer) }
  }, [path, locked, inFlight, onChanged])

  function change(next: EventData) {
    setDraft(next)
    setDirty(true)
    onDirty(true)
    setVerdict(null)
    setPreview(null)
    setNotice('')
  }

  function accept(current: SantaEvent) {
    setEvent(current)
    setDraft(current.data)
    setDirty(false)
    onDirty(false)
    onChanged(current)
  }

  async function perform(operation: () => Promise<void>) {
    setBusy(true)
    setError('')
    setNotice('')
    try { await operation() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Opération impossible.') }
    finally { setBusy(false) }
  }

  async function save(): Promise<SantaEvent> {
    if (!dirty) return event
    const current = await api<SantaEvent>(path, 'PUT', { revision: event.revision, data: draft })
    accept(current)
    return current
  }

  async function send(retry_uncertain = false) {
    const secret = password
    setPassword('')
    setSending(true)
    try {
      const current = await api<SantaEvent>(`${path}/send`, 'POST', { password: secret, retry_uncertain })
      accept(current)
      setStatuses(await api<DeliveryStatus[]>(`${path}/deliveries`))
      setNotice(current.state === 'sent'
        ? 'Tous les mails ont été acceptés par Gmail. Cela ne garantit pas leur livraison.'
        : 'Envoi arrêté : consultez le suivi avant de reprendre.')
    } finally { setSending(false) }
  }

  function insertTag(tag: string) {
    const input = target === 'body' ? bodyRef.current : subjectRef.current
    const value = draft[target]
    const start = input?.selectionStart ?? value.length
    const end = input?.selectionEnd ?? start
    const token = `{{${tag}}}`
    change({ ...draft, [target]: value.slice(0, start) + token + value.slice(end) })
    requestAnimationFrame(() => {
      input?.focus()
      input?.setSelectionRange(start + token.length, start + token.length)
    })
  }

  const accepted = event.counts.accepted ?? 0
  return (
    <article className="editor">
      <header className="event-heading">
        <div><p className="eyebrow">Votre événement</p><h2>{event.data.name}</h2></div>
        <span className={`badge ${event.state}`}>{stateLabels[event.state]}</span>
      </header>
      {error && <div role="alert" className="alert error">{error}</div>}
      {notice && <div role="status" className="alert success">{notice}</div>}
      {locked && <div className="alert">
        Le tirage est verrouillé. Pour changer la configuration, dupliquez cet événement.
      </div>}
      <form onSubmit={submit => {
        submit.preventDefault()
        void perform(async () => { await save(); setNotice('Brouillon enregistré.') })
      }}>
        <fieldset disabled={locked || disabled}>
          <section className="card">
            <div className="section-title"><span className="step">01</span><h3>Les petits détails</h3></div>
            <div className="fields">
              <label>Nom de l'événement<input required maxLength={120} value={draft.name}
                onChange={e => change({ ...draft, name: e.target.value })} /></label>
              <label>Adresse Gmail expéditrice<input type="email" placeholder="vous@gmail.com"
                value={draft.sender ?? ''} autoComplete="email"
                onChange={e => change({ ...draft, sender: e.target.value || null })} /></label>
              <label>Budget par cadeau (facultatif)<input type="number" min="0.01" max="1000000"
                step="0.01" value={draft.budget ?? ''}
                onChange={e => change({ ...draft, budget: e.target.value ? Number(e.target.value) : null })} /></label>
              <label>Devise<select value={draft.currency}
                onChange={e => change({ ...draft, currency: e.target.value })}>
                {['EUR', 'USD', 'GBP', 'CHF', 'CAD'].map(value => <option key={value}>{value}</option>)}
              </select></label>
              <label>Date du cadeau (facultative)<input type="date" value={draft.gift_date ?? ''}
                onChange={e => change({ ...draft, gift_date: e.target.value || null })} /></label>
            </div>
          </section>
          <section className="card">
            <div className="section-title"><span className="step">02</span><h3>Qui participe ?</h3>
              <span className="muted">{draft.participants.length} / 200</span></div>
            <p>Un nom, une adresse unique, et chacun reçoit son petit secret.</p>
            {draft.participants.length === 0 && <p className="empty">Ajoutez vos premiers participants.</p>}
            {draft.participants.map((person, index) => <div className="participant" key={person.id}>
              <span className="avatar">{String(index + 1).padStart(2, '0')}</span>
              <label>Nom {index + 1}<input required maxLength={120} value={person.name}
                onChange={e => change({ ...draft, participants: draft.participants.map(p =>
                  p.id === person.id ? { ...p, name: e.target.value } : p) })} /></label>
              <label>Mail {index + 1}<input type="email" required value={person.email}
                onChange={e => change({ ...draft, participants: draft.participants.map(p =>
                  p.id === person.id ? { ...p, email: e.target.value } : p) })} /></label>
              <button type="button" className="subtle" aria-label={`Retirer le participant ${index + 1}`}
                onClick={() => change({
                  ...draft, participants: draft.participants.filter(p => p.id !== person.id),
                  groups: draft.groups.map(group => ({ ...group,
                    members: group.members.filter(id => id !== person.id) }))
                    .filter(group => group.members.length >= 2),
                })}>Retirer</button>
            </div>)}
            <button type="button" disabled={draft.participants.length >= 200}
              onClick={() => change({ ...draft, participants: [...draft.participants,
                { id: crypto.randomUUID(), name: '', email: '' }] })}>+ Ajouter une personne</button>
          </section>
          <section className="card">
            <div className="section-title"><span className="step">03</span><h3>Les groupes d'exclusion</h3></div>
            <p>Couples, foyer… Les membres d'un même groupe ne pourront pas s'offrir de cadeaux entre eux.
              Une personne peut appartenir à plusieurs groupes.</p>
            <p className="muted">Au moins deux membres par groupe. Retirer un participant supprime aussi
              les groupes devenus trop petits.</p>
            {draft.groups.map((group, index) => <div className="group" key={group.id}>
              <div className="actions">
                <label>Nom du groupe {index + 1}<input required maxLength={120} value={group.name}
                  onChange={e => change({ ...draft, groups: draft.groups.map(g =>
                    g.id === group.id ? { ...g, name: e.target.value } : g) })} /></label>
                <button type="button" onClick={() => change({ ...draft,
                  groups: draft.groups.filter(g => g.id !== group.id) })}>Supprimer le groupe</button>
              </div>
              <div className="choices" role="group" aria-label={`Membres du groupe ${index + 1}`}>
                {draft.participants.map((person, personIndex) => <label className="choice" key={person.id}>
                  <input type="checkbox" checked={group.members.includes(person.id)}
                    onChange={e => change({ ...draft, groups: draft.groups.map(g => g.id === group.id
                      ? { ...g, members: e.target.checked ? [...g.members, person.id]
                        : g.members.filter(id => id !== person.id) } : g) })} />
                  {person.name || `Personne ${personIndex + 1}`}
                </label>)}
              </div>
            </div>)}
            <button type="button" disabled={draft.participants.length < 2 || draft.groups.length >= 200}
              onClick={() => change({ ...draft, groups: [...draft.groups, {
                id: crypto.randomUUID(), name: `Groupe ${draft.groups.length + 1}`, members: [],
              }] })}>+ Ajouter un groupe</button>
          </section>
          <section className="card">
            <div className="section-title"><span className="step">04</span><h3>Un message à votre image</h3></div>
            <p>Le participant reçoit le mail et offre le cadeau. Le destinataire reçoit le cadeau.</p>
            <label>Objet<input required maxLength={300} value={draft.subject} ref={subjectRef}
              onFocus={() => setTarget('subject')}
              onChange={e => change({ ...draft, subject: e.target.value })} /></label>
            <label>Message<textarea rows={9} required maxLength={20000} value={draft.body} ref={bodyRef}
              onFocus={() => setTarget('body')}
              onChange={e => change({ ...draft, body: e.target.value })} /></label>
            <p className="muted">Habillage Noël ultra kitsch inclus : sapin scintillant, cadeaux
              animés et paillettes ! Votre message reste en texte simple, sans HTML à saisir.
              Les GIFs sont intégrés au mail, sans images externes.</p>
            <p className="muted">Insérer dans {target === 'body' ? 'le message' : "l'objet"} :</p>
            <div className="tags">{tags.map(tag => <button type="button" key={tag}
              onClick={() => insertTag(tag)}>{`{{${tag}}}`}</button>)}</div>
          </section>
        </fieldset>
        {!locked && <div className="actions save-bar">
          <button type="submit" className="primary" disabled={disabled || !dirty}>Enregistrer le brouillon</button>
          <span className="muted">{dirty ? 'Modifications non enregistrées' : 'Tout est enregistré'}</span>
        </div>}
      </form>

      <section className="card">
        <h3>Vérifier avant de se lancer</h3>
        <div className="actions">
          <button disabled={disabled} onClick={() => { void perform(async () => {
            setVerdict(await api<Verdict>('/validate', 'POST', draft))
          }) }}>Vérifier la faisabilité</button>
          <button disabled={disabled} onClick={() => { void perform(async () => {
            setPreview(await api<Preview>('/preview', 'POST', draft))
          }) }}>Aperçu fictif du mail</button>
        </div>
        {verdict && <p role="status" className={`alert ${verdict.possible ? 'success' : 'error'}`}>
          {verdict.message}</p>}
        {preview && <div className="preview">
          <strong>Aperçu fictif — Camille offre un cadeau à Alex</strong>
          <p>Objet : {preview.subject}</p>
          <iframe className="mail-preview" title="Aperçu du mail de Noël"
            sandbox="" referrerPolicy="no-referrer" srcDoc={preview.html} />
          <details><summary>Version texte simple</summary><pre>{preview.body}</pre></details>
          <p className="muted">Selon la messagerie, les images peuvent être masquées ou les GIFs
            rester fixes. Le message reste lisible sans elles.</p>
        </div>}
        {!locked && <button className="primary" disabled={disabled || !verdict?.possible || !draft.sender}
          onClick={() => setConfirmation('draw')}>Effectuer le tirage</button>}
        {!locked && <p className="muted">Le tirage nécessite une configuration possible et une adresse
          Gmail. Il verrouillera l'événement sans envoyer de mail immédiatement.</p>}
      </section>

      <section className="card">
        <div className="section-title"><span className="step">05</span><h3>Chut… c'est dans la boîte</h3></div>
        <p>Activez la validation en deux étapes Google, puis créez un{' '}
          <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">
            mot de passe d'application</a>. N'utilisez jamais votre mot de passe Gmail habituel.</p>
        <label>Mot de passe d'application Gmail<input type="password" autoComplete="off"
          value={password} disabled={disabled} placeholder="16 lettres, espaces acceptés"
          onChange={e => setPassword(e.target.value)} /></label>
        <p className="muted">Utilisé uniquement pour cette opération, jamais sauvegardé.
          Le compte Gmail doit correspondre à l'adresse expéditrice.</p>
        <div className="actions">
          <button disabled={disabled || !password || !draft.sender} onClick={() => {
            const secret = password
            setPassword('')
            void perform(async () => {
              await save()
              const result = await api<MailResult>(`${path}/test-mail`, 'POST', { password: secret })
              if (result.status !== 'accepted') throw new Error(result.error ?? 'Envoi du test non confirmé.')
              setNotice("Mail de test fictif accepté par Gmail, envoyé uniquement à l'expéditeur.")
            })
          }}>M'envoyer un test fictif</button>
          {locked && event.state !== 'sent' && <button className="primary"
            disabled={disabled || !password} onClick={() => {
              if ((event.counts.uncertain ?? 0) > 0) setConfirmation('retry')
              else void perform(() => send())
            }}>{event.state === 'drawn' ? 'Envoyer les attributions' : 'Reprendre les envois'}</button>}
        </div>
        {locked && <>
          <p aria-live="polite">{accepted} / {draft.participants.length} mails acceptés par Gmail</p>
          <progress value={accepted} max={draft.participants.length} aria-label="Progression des envois" />
          {inFlight && <p role="status">Envoi en cours. Gardez cette page et le serveur ouverts.</p>}
          <ul className="delivery-list">{statuses.map((status, index) =>
            <li key={index}><strong>{status.giver}</strong><span>{deliveryLabels[status.status]}</span>
              {status.error && <p className="error-text">{status.error}</p>}</li>)}</ul>
        </>}
        <p className="muted">Un mail accepté par Gmail peut être retardé, rejeté plus tard ou classé
          dans les indésirables. Les quotas Gmail restent applicables.</p>
      </section>

      {locked && <section className="card confidential">
        <h3>Les secrets sont bien gardés</h3>
        <p>Les attributions ne sont jamais affichées automatiquement.</p>
        {assignments === null
          ? <button disabled={disabled} onClick={() => setConfirmation('reveal')}>Consulter les attributions…</button>
          : <><button onClick={() => setAssignments(null)}>Masquer les attributions</button>
            <ul>{assignments.map((item, index) =>
              <li key={index}><strong>{item.giver}</strong> offre à <strong>{item.recipient}</strong></li>)}</ul></>}
      </section>}
      <footer className="actions event-tools">
        <button disabled={disabled} onClick={() => { void perform(async () => {
          await save()
          onDuplicate(await api<SantaEvent>(`${path}/duplicate`, 'POST', { confirm: true }))
        }) }}>Dupliquer l'événement</button>
        <button className="danger" disabled={disabled} onClick={() => setConfirmation('delete')}>
          Supprimer l'événement</button>
      </footer>
      {confirmation && <Confirm
        title={{
          draw: 'Prêt à garder le secret ?', reveal: 'Attention : vous allez découvrir les secrets',
          delete: "Supprimer cet événement ?", retry: 'Risque de mails en double',
        }[confirmation]}
        accept={{
          draw: 'Confirmer le tirage', reveal: 'Je confirme, révéler les attributions',
          delete: 'Supprimer définitivement', retry: 'Confirmer et reprendre',
        }[confirmation]}
        onClose={() => setConfirmation(null)}
        onAccept={() => {
          const action = confirmation
          setConfirmation(null)
          void perform(async () => {
            if (action === 'draw') {
              const saved = await save()
              accept(await api<SantaEvent>(`${path}/draw`, 'POST', { revision: saved.revision }))
              setNotice('Tirage enregistré. Vous pouvez maintenant envoyer les mails.')
            } else if (action === 'reveal') {
              setAssignments(await api<Assignment[]>(`${path}/reveal`, 'POST', { confirm: true }))
            } else if (action === 'delete') {
              await api(path, 'DELETE', { confirm: true })
              onDeleted()
            } else await send(true)
          })
        }}>
        {confirmation === 'draw' && <p>Les participants, exclusions et messages seront verrouillés.
          Aucun mail ne sera envoyé à cette étape. Pour recommencer, il faudra dupliquer l'événement.</p>}
        {confirmation === 'reveal' && <p>Vous allez voir qui offre à qui, y compris votre propre
          attribution. Assurez-vous que personne ne regarde votre écran. Cette action gâche la surprise.</p>}
        {confirmation === 'delete' && <p>La configuration, les attributions et le suivi seront effacés.
          Les mails déjà envoyés ne peuvent pas être annulés.</p>}
        {confirmation === 'retry' && <p>Certains mails ont peut-être déjà été acceptés par Gmail.
          Vérifiez les messages envoyés avant de réessayer : les participants pourraient recevoir un doublon.
          Les attributions resteront identiques.</p>}
      </Confirm>}
    </article>
  )
}
