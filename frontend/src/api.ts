export interface Participant { id: string; name: string; email: string }
export interface Group { id: string; name: string; members: string[] }
export interface EventData {
  name: string
  budget: number | null
  currency: string
  gift_date: string | null
  sender: string | null
  participants: Participant[]
  groups: Group[]
  subject: string
  body: string
}
export interface SantaEvent {
  id: string
  revision: number
  state: string
  data: EventData
  counts: Record<string, number>
}
export interface Verdict { possible: boolean; message: string }
export interface Preview { subject: string; body: string }
export interface Assignment { giver: string; recipient: string }
export interface DeliveryStatus { giver: string; status: string; error: string | null }
export interface MailResult { status: string; error: string | null }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: method === 'GET' ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: 'no-store',
  })
  if (!response.ok) {
    const result: { detail?: string | { loc: string[]; msg: string }[] } = await response.json()
    const message = typeof result.detail === 'string'
      ? result.detail
      : result.detail?.map(error => `${error.loc.slice(1).join('.')} : ${error.msg}`).join('\n')
    throw new Error(message || `Erreur serveur (${response.status}).`)
  }
  return response.json() as Promise<T>
}

export const stateLabels: Record<string, string> = {
  draft: 'Brouillon', drawn: 'Tirage verrouillé', sending: 'Envoi en cours',
  partial: 'Envoi à reprendre', sent: 'Mails acceptés par Gmail',
}
export const deliveryLabels: Record<string, string> = {
  pending: 'En attente', sending: 'En cours', accepted: 'Accepté par Gmail',
  failed: 'Échec', uncertain: 'À vérifier dans Gmail',
}
