import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, type SantaEvent } from './api'
import { Editor } from './Editor'

vi.mock('./api', async importOriginal => ({
  ...await importOriginal<typeof import('./api')>(),
  api: vi.fn(),
}))
const mockedApi = vi.mocked(api)

const draft: SantaEvent = {
  id: 'event-1', revision: 1, state: 'draft', counts: {},
  data: {
    name: 'Noël des amis', budget: null, currency: 'EUR', gift_date: null,
    sender: 'organisateur@gmail.com', subject: 'Secret pour {{participant_nom}}',
    body: '{{participant_nom}} offre à {{destinataire_nom}}',
    participants: [
      { id: 'person-1', name: 'Camille', email: 'camille@example.com' },
      { id: 'person-2', name: 'Alex', email: 'alex@example.com' },
    ], groups: [],
  },
}
const drawn: SantaEvent = { ...draft, state: 'drawn', revision: 2, counts: { pending: 2 } }

function setup(event = draft) {
  return render(<Editor initial={structuredClone(event)} onChanged={vi.fn()} onDirty={vi.fn()}
    onDuplicate={vi.fn()} onDeleted={vi.fn()} />)
}

beforeEach(() => {
  mockedApi.mockReset()
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
})

describe('éditeur Secret Santa', () => {
  it('invalide la faisabilité dès une modification', async () => {
    mockedApi.mockResolvedValue({ possible: true, message: 'Configuration possible' })
    setup()
    expect(screen.getByRole('button', { name: 'Effectuer le tirage' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier la faisabilité' }))
    expect(await screen.findByText('Configuration possible')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Effectuer le tirage' })).toBeEnabled()
    await userEvent.type(screen.getByLabelText("Nom de l'événement"), ' !')
    expect(screen.queryByText('Configuration possible')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Effectuer le tirage' })).toBeDisabled()
  })

  it('montre une impossibilité et les erreurs API', async () => {
    mockedApi.mockResolvedValueOnce({ possible: false, message: 'Exclusions incompatibles' })
    setup()
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier la faisabilité' }))
    expect(await screen.findByText('Exclusions incompatibles')).toBeVisible()
    mockedApi.mockRejectedValueOnce(new Error('Adresse mail en double'))
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier la faisabilité' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Adresse mail en double')
  })

  it('ajoute un groupe et sélectionne ses membres', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: '+ Ajouter un groupe' }))
    const members = screen.getAllByRole('checkbox')
    await userEvent.click(members[0])
    await userEvent.click(members[1])
    expect(members[0]).toBeChecked()
    expect(members[1]).toBeChecked()
  })

  it('ne charge les attributions qu’après la confirmation du second clic', async () => {
    mockedApi.mockImplementation(async path => {
      if (path.endsWith('/reveal')) return [{ giver: 'Camille', recipient: 'Alex' }]
      if (path.endsWith('/deliveries')) return []
      return drawn
    })
    setup(drawn)
    await waitFor(() => expect(mockedApi).toHaveBeenCalled())
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/reveal'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Consulter les attributions…' }))
    expect(screen.getByRole('dialog')).toBeVisible()
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/reveal'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/reveal'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Consulter les attributions…' }))
    await userEvent.click(screen.getByRole('button', { name: 'Je confirme, révéler les attributions' }))
    expect(await screen.findByText('offre à', { exact: false, selector: 'li' })).toBeVisible()
    expect(mockedApi).toHaveBeenCalledWith('/events/event-1/reveal', 'POST', { confirm: true })
    await userEvent.click(screen.getByRole('button', { name: 'Masquer les attributions' }))
    expect(screen.queryByText('offre à', { exact: false, selector: 'li' })).not.toBeInTheDocument()
  })

  it('efface le secret après un test et utilise des données fictives', async () => {
    mockedApi.mockResolvedValue({ status: 'accepted', error: null })
    setup()
    const password = screen.getByLabelText("Mot de passe d'application Gmail")
    fireEvent.change(password, { target: { value: 'abcdefghijklmnop' } })
    await userEvent.click(screen.getByRole('button', { name: "M'envoyer un test fictif" }))
    expect(password).toHaveValue('')
    expect(await screen.findByRole('status')).toHaveTextContent('Mail de test fictif accepté')
    expect(mockedApi).toHaveBeenCalledWith('/events/event-1/test-mail', 'POST', { password: 'abcdefghijklmnop' })
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('verrouille le formulaire et affiche le suivi sans destinataire', async () => {
    mockedApi.mockImplementation(async path => path.endsWith('/deliveries')
      ? [{ giver: 'Camille', status: 'accepted', error: null }]
      : { ...drawn, counts: { accepted: 1, pending: 1 } })
    setup(drawn)
    expect(screen.getByLabelText("Nom de l'événement")).toBeDisabled()
    expect(await screen.findByText('Accepté par Gmail')).toBeVisible()
    expect(screen.getByRole('progressbar')).toHaveAttribute('value', '1')
    expect(screen.queryByRole('button', { name: 'Effectuer le tirage' })).not.toBeInTheDocument()
  })

  it('demande confirmation avant de reprendre les envois incertains', async () => {
    const partial = { ...drawn, state: 'partial', counts: { uncertain: 1, pending: 1 } }
    mockedApi.mockImplementation(async (path, method) => {
      if (path.endsWith('/deliveries')) return []
      if (path.endsWith('/send') && method === 'POST') {
        return { ...partial, state: 'sent', counts: { accepted: 2 } }
      }
      return partial
    })
    setup(partial)
    await waitFor(() => expect(mockedApi).toHaveBeenCalled())
    fireEvent.change(screen.getByLabelText("Mot de passe d'application Gmail"),
      { target: { value: 'abcdefghijklmnop' } })
    await userEvent.click(screen.getByRole('button', { name: 'Reprendre les envois' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Risque de mails en double')
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/send'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Confirmer et reprendre' }))
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(
      '/events/event-1/send', 'POST', { password: 'abcdefghijklmnop', retry_uncertain: true }))
    expect(screen.getByLabelText("Mot de passe d'application Gmail")).toHaveValue('')
  })

  it('confirme le tirage et ne déclenche pas l’envoi', async () => {
    mockedApi.mockImplementation(async path => {
      if (path === '/validate') return { possible: true, message: 'Configuration possible' }
      if (path.endsWith('/deliveries')) return []
      return drawn
    })
    setup()
    await userEvent.click(screen.getByRole('button', { name: 'Vérifier la faisabilité' }))
    await userEvent.click(screen.getByRole('button', { name: 'Effectuer le tirage' }))
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/draw'))).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Confirmer le tirage' }))
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith('/events/event-1/draw', 'POST', { revision: 1 }))
    expect(mockedApi.mock.calls.some(([path]) => path.endsWith('/send'))).toBe(false)
    expect(await screen.findByText('Tirage enregistré. Vous pouvez maintenant envoyer les mails.')).toBeVisible()
  })
})
