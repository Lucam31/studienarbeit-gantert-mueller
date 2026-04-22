import { useState, useEffect } from 'react'
import reactLogo from '.././assets/react.svg'
import viteLogo from '/vite.svg'

export default function WebsocketView() {
    const [socket, setSocket] = useState<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [message, setMessage] = useState('')
    const [count, setCount] = useState(0)

    useEffect(() => {
        const wsUrl =
        (import.meta as any).env?.VITE_WS_URL || `ws://${window.location.hostname}:50000`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log('Connected to WebSocket server:', wsUrl)
            setIsConnected(true)
        }

        ws.onmessage = (event) => {
            console.log('Message from server:', event.data)
        }

        ws.onclose = (event) => {
            console.log(
                'Disconnected from WebSocket server:',
                `code=${event.code}`,
                `reason=${event.reason || '(none)'}`
            )
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
            id: 'drive_command',
            payload: {
            speed: 50,
            steering: 0,
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
