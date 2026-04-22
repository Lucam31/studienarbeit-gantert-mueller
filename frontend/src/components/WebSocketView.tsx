import { useState, useEffect, useRef } from 'react'
import { Joystick } from 'react-joystick-component';

export default function WebsocketView() {
    const [socket, setSocket] = useState<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [message, setMessage] = useState('')
    const [joystickKey, setJoystickKey] = useState(0)
    const lastMoveSentAtRef = useRef(0)
    const lastSpeed = useRef(0)
    const lastSteering = useRef(0)

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
            speed: message,
            steering: 0,
            },
        }
        socket.send(JSON.stringify(jsonMessage))
        console.log('Message sent:', jsonMessage)
        } else {
        console.error('WebSocket is not connected')
        }
    }

    const handleMove = (event: any) => {
        const { x, y } = event
        console.log('Joystick move:', { x, y })

        const now = Date.now()
        // if (now - lastMoveSentAtRef.current < 300) {
        //     return
        // }

        const speed = Math.round(Math.round(y  * 100)/5)*5 // Convert to range -100 to 100
        const steering = Math.round(Math.round(x  * 100)/5)*5 // Convert to range -100 to 100
        if (speed === lastSpeed.current && steering === lastSteering.current) {
            return
        }
        lastSpeed.current = speed
        lastSteering.current = steering
        const jsonMessage = {
            id: 'drive_command',
            payload: {
                x: steering,
                y: speed,
            },
        }
        if (socket && isConnected) {
            socket.send(JSON.stringify(jsonMessage))
            lastMoveSentAtRef.current = now
            console.log('Joystick move message sent:', jsonMessage)
        } else {
            console.error('WebSocket is not connected')
        }
    }

    const handleStop = () => {
        const jsonMessage = {
            id: 'drive_command',
            payload: {
                x: 0,
                y: 0,
            },
        }
        if (socket && isConnected) {
            socket.send(JSON.stringify(jsonMessage))
            console.log('Joystick stop message sent:', jsonMessage)
        } else {
            console.error('WebSocket is not connected')
        }

        // With sticky=true, remounting clears internal stick coordinates back to center.
        setJoystickKey((prev) => prev + 1)
    }

    return (
        <>
        <div className="websocket">
            <Joystick key={joystickKey} size={100} sticky={true} baseColor="rgba(171, 163, 163, 0.14)" stickColor="rgb(178, 35, 35)" move={handleMove} stop={handleStop}></Joystick>
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
