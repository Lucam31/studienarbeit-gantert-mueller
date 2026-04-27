import { useEffect, useRef, useState } from "react";
import { WebRTCReader } from "./WebRTCReader";
import { Joystick } from 'react-joystick-component';

export default function MainView() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const readerRef = useRef<WebRTCReader | null>(null);
  const [aspectRatio, setAspectRatio] = useState(16 / 9);

  const [socket, setSocket] = useState<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [joystickKey, setJoystickKey] = useState(0)
    const lastMoveSentAtRef = useRef(0)
    const lastSpeed = useRef(0)
    const lastSteering = useRef(0)
    const autopilotEnabled = useRef(false)

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

    const toggleAutopilot = () => {
        
      if (autopilotEnabled.current) {
        stopVision()
      } else {
        startVision()
      }
      autopilotEnabled.current = !autopilotEnabled.current 
    }

    const startVision = () => {
      const message = {
        id: "follow_line_command",
        payload: { action: "start" }
      }
      if (socket && isConnected) {
            socket.send(JSON.stringify(message))
            console.log('Start vision message sent:', message)
        } else {
            console.error('WebSocket is not connected')
        }
    }

    const stopVision = () => {
      const message = {
        id: "follow_line_command",
        payload: { action: "stop" }
      }
      if (socket && isConnected) {
            socket.send(JSON.stringify(message))
            console.log('Stop vision message sent:', message)
        } else {
            console.error('WebSocket is not connected')
        }
    }

  useEffect(() => {
    readerRef.current = new WebRTCReader({
      url: "http://192.168.178.81:8889/cam/whep",
      onError: (err: Error) => {
        console.error("WebRTC Error:", err);
      },
      onTrack: (evt: RTCTrackEvent) => {
        if (videoRef.current && evt.streams[0]) {
          console.log("Setting video stream");
          videoRef.current.srcObject = evt.streams[0];
        }
      },
    });

    return () => {
      if (readerRef.current) {
        readerRef.current.close();
        readerRef.current = null;
      }
    };
  }, []);

  const handleVideoMetadata = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      return;
    }

    setAspectRatio(video.videoWidth / video.videoHeight);
  };



  return (
    <div className="flex w-full min-h-dvh p-4 gap-4">
      <div className="flex flex-col justify-center">
        <Joystick key={joystickKey} size={100} sticky={true} baseColor="rgba(171, 163, 163, 0.14)" stickColor="rgb(178, 35, 35)" move={handleMove} stop={handleStop}></Joystick>
      </div>
      
      <div className="flex w-full flex-1 items-center justify-center p-4">
        <div
          className="relative w-full overflow-hidden rounded-lg bg-black"
          style={{ aspectRatio }}
        >
          <video
            ref={videoRef}
            muted
            autoPlay
            playsInline
            onLoadedMetadata={handleVideoMetadata}
            className="absolute inset-0 h-full w-full object-contain"
          />
        </div>
      </div>
      
      <div className="flex items-center">
        <button className="p-4 bg-red-600 rounded-2xl text-white" onClick={() => toggleAutopilot()}>
          Mode
        </button>
      </div>
    </div>
  );
}