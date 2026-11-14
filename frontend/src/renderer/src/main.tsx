import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
// Library styles first, then ours: our rules have to win the cascade.
import '@xyflow/react/dist/style.css'
import './styles/tokens.css'
import './styles/app.css'

const container = document.getElementById('root')
if (!container) throw new Error('The #root element is missing from index.html')

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>
)