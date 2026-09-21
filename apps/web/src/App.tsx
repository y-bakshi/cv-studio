import { useEffect, useState } from 'react'
import { LoaderCircle } from 'lucide'

import Auth from './components/Auth'
import { MorphGlyph } from './components/MorphGlyph'
import { Workspace } from './features/workspace/Workspace'
import { api } from './lib/api'
import type { User } from './lib/types'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api<User>('/api/auth/me')
      .then(setUser)
      .catch(() => undefined)
      .finally(() => setLoading(false))
  }, [])

  const logout = async () => {
    await api('/api/auth/logout', { method: 'POST' })
    setUser(null)
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <MorphGlyph icon={LoaderCircle} className="spin" />Loading CV Studio
      </div>
    )
  }

  if (!user) {
    return <Auth onAuthenticated={setUser} />
  }

  return <Workspace user={user} onLogout={() => void logout()} />
}
