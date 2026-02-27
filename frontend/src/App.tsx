import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [message, setMessage] = useState('')
  const [count, setCount] = useState(0)

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:50000')

    ws.onopen = () => {
      console.log('Connected to WebSocket server')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      console.log('Message from server:', event.data)
    }

    ws.onclose = () => {
      console.log('Disconnected from WebSocket server')
      setIsConnected(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    setSocket(ws)

    return () => {
      ws.close()
    }
  }, [])

  const sendMessage = () => {
    if (socket && isConnected) {
      const jsonMessage = {
        id: 'frontend_example',
        payload: {
          key: message,
          timestamp: new Date().toISOString(),
        },
      }
      socket.send(JSON.stringify(jsonMessage))
      console.log('Message sent:', jsonMessage)
    } else {
      console.error('WebSocket is not connected')
    }
  }

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      <div className="websocket">
        <h2>WebSocket</h2>
        <button onClick={sendMessage} disabled={!isConnected}>
          Send JSON Message
        </button>
        <p>{isConnected ? 'Connected to WebSocket server' : 'Disconnected'}</p>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message here"
        />
      </div>
    </>
  )
}

export default App
