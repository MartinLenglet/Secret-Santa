import { useEffect, useRef } from 'react'

export function Confirm({ title, children, accept, onAccept, onClose }: {
  title: string
  children: React.ReactNode
  accept: string
  onAccept: () => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { ref.current?.showModal() }, [])
  return (
    <dialog ref={ref} aria-labelledby="confirm-title" onCancel={event => {
      event.preventDefault()
      onClose()
    }}>
      <h2 id="confirm-title">{title}</h2>
      <div className="dialog-copy">{children}</div>
      <div className="actions">
        <button autoFocus onClick={onClose}>Annuler</button>
        <button className="primary" onClick={onAccept}>{accept}</button>
      </div>
    </dialog>
  )
}
