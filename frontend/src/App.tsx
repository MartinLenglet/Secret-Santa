import { useCallback, useEffect, useState } from 'react'
import { api, stateLabels, type SantaEvent } from './api'
import { Editor } from './Editor'
import './App.css'

function App() {
  const [events, setEvents] = useState<SantaEvent[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    void api<SantaEvent[]>('/events').then(current => {
      if (active) { setEvents(current); setError('') }
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : 'Chargement impossible.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  function canLeave() {
    return !dirty || window.confirm('Quitter sans enregistrer les modifications ?')
  }
  function select(id: string) {
    if (id !== selected && canLeave()) { setDirty(false); setSelected(id) }
  }
  const changed = useCallback((event: SantaEvent) => {
    setEvents(current => current.map(item => item.id === event.id ? event : item))
  }, [])
  const active = events.find(event => event.id === selected)
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={e => {
          e.preventDefault()
          if (canLeave()) { setSelected(null); setDirty(false) }
        }}><span className="brand-mark" aria-hidden="true">S</span> Secret Santa<span className="brand-dot">.</span></a>
        <span className="local-label">PRIVÉ · SUR VOTRE MACHINE</span>
        <button className="primary new-event" disabled={creating || loading} onClick={() => {
          if (!canLeave()) return
          setCreating(true)
          setError('')
          void api<SantaEvent>('/events', 'POST', {}).then(event => {
            setEvents(current => [...current, event])
            setSelected(event.id)
            setDirty(false)
          }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Création impossible.'))
            .finally(() => setCreating(false))
        }}>+ Nouvel événement</button>
        <p className="nav-label">VOS ÉVÉNEMENTS</p>
        <nav aria-label="Événements">
          {events.map(event => <button key={event.id} className={event.id === selected ? 'event active' : 'event'}
            aria-current={event.id === selected ? 'page' : undefined} onClick={() => select(event.id)}>
            <strong>{event.data.name}</strong><small>{stateLabels[event.state]}</small>
          </button>)}
          {!loading && events.length === 0 && <p className="muted">Vos prochaines surprises commencent ici.</p>}
        </nav>
        <div className="sidebar-note"><strong>Un cadeau. Un secret. Un sourire.</strong>
          <p>Vos événements restent dans votre base locale. Seuls les mails passent par Gmail.</p></div>
      </aside>
      <main>
        <header className="topbar"><span>L'atelier des petites attentions</span><span className="privacy-dot">Mode local</span></header>
        {error && <div className="alert error" role="alert">{error}{' '}
          <button onClick={() => { setLoading(true); setReload(value => value + 1) }}>
            Réessayer le chargement</button></div>}
        {loading && <p role="status">Chargement de vos événements…</p>}
        {active ? <Editor key={active.id} initial={active} onChanged={changed} onDirty={setDirty}
          onDuplicate={event => {
            setEvents(current => [...current, event]); setSelected(event.id); setDirty(false)
          }}
          onDeleted={() => {
            setEvents(current => current.filter(event => event.id !== selected))
            setSelected(null); setDirty(false)
          }} /> : <section className="welcome">
          <p className="eyebrow">Les meilleures surprises se préparent en secret</p>
          <h1>Un peu de mystère.<br /><em>Beaucoup d'attention.</em></h1>
          <p>Réunissez vos proches, laissez le hasard faire les présentations
            et offrez à chacun une jolie surprise.</p>
          <div className="welcome-cards">
            <div><span>01</span><h2>Rassemblez</h2><p>Vos participants et leurs groupes d'exclusion.</p></div>
            <div><span>02</span><h2>Personnalisez</h2><p>Un message qui ne ressemble qu'à vous.</p></div>
            <div><span>03</span><h2>Surprenez</h2><p>Un tirage fiable, un mail privé pour chacun.</p></div>
          </div>
          <p className="muted">Commencez avec « Nouvel événement » ou retrouvez un événement dans le menu.</p>
        </section>}
        <footer className="page-footer">Vos données et les attributions sont conservées en clair dans SQLite.
          Protégez votre machine et votre compte Gmail. Les messages envoyés peuvent y révéler les résultats.</footer>
      </main>
    </div>
  )
}

export default App
