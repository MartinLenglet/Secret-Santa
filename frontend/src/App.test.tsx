import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { api, type SantaEvent } from './api'

vi.mock('./api', async importOriginal => ({
  ...await importOriginal<typeof import('./api')>(),
  api: vi.fn(),
}))
const mockedApi = vi.mocked(api)
beforeEach(() => mockedApi.mockReset())

it('charge la liste, crée un événement puis enregistre ses modifications', async () => {
  const event: SantaEvent = {
    id: 'new-event', revision: 1, state: 'draft', counts: {},
    data: {
      name: 'Mon Secret Santa', participants: [], groups: [], budget: null,
      currency: 'EUR', gift_date: null, sender: null, subject: 'Secret', body: 'Bonjour',
    },
  }
  mockedApi.mockResolvedValueOnce([])
  render(<App />)
  await waitFor(() => expect(screen.getByRole('button', { name: '+ Nouvel événement' })).toBeEnabled())
  mockedApi.mockResolvedValueOnce(event)
  await userEvent.click(screen.getByRole('button', { name: '+ Nouvel événement' }))
  const name = await screen.findByLabelText("Nom de l'événement")
  await userEvent.clear(name)
  await userEvent.type(name, 'Famille')
  const updated = { ...event, revision: 2, data: { ...event.data, name: 'Famille' } }
  mockedApi.mockResolvedValueOnce(updated)
  await userEvent.click(screen.getByRole('button', { name: 'Enregistrer le brouillon' }))
  expect(await screen.findByText('Brouillon enregistré.')).toBeVisible()
  expect(mockedApi).toHaveBeenLastCalledWith('/events/new-event', 'PUT', {
    revision: 1, data: updated.data,
  })
  expect(screen.getByRole('heading', { name: 'Famille' })).toBeVisible()
})

it('permet de reprendre un chargement en erreur', async () => {
  mockedApi.mockRejectedValueOnce(new Error('Serveur indisponible'))
  render(<App />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Serveur indisponible')
  mockedApi.mockResolvedValueOnce([])
  await userEvent.click(screen.getByRole('button', { name: 'Réessayer le chargement' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  expect(screen.getByRole('button', { name: '+ Nouvel événement' })).toBeEnabled()
})
