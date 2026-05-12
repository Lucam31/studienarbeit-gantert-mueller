import { useEffect, useRef, useState } from "react";
import { WebRTCReader } from "./WebRTCReader";
import { Joystick } from 'react-joystick-component';

export default function MainView() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const readerRef = useRef<WebRTCReader | null>(null);
  const [aspectRatio, setAspectRatio] = useState(16 / 9);
  const [joystickSize, setJoystickSize] = useState(200);
  const [joystickStickSize, setJoystickStickSize] = useState(100);
  const [distanceCm, setDistanceCm] = useState<number | null>(null);
  const [emergencyStopActive, setEmergencyStopActive] = useState(false);

  const [socket, setSocket] = useState<WebSocket | null>(null)
    const [isConnected, setIsConnected] = useState(false)
    const [joystickKey, setJoystickKey] = useState(0)
    const [speed, setSpeed] = useState(0)
    const lastSpeed = useRef(0)
    const lastSteering = useRef(0)
    const autopilotEnabled = useRef(false)

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const media = window.matchMedia("(max-width: 640px)");
    const updateSizes = () => {
      setJoystickSize(media.matches ? 75 : 150);
      setJoystickStickSize(media.matches ? 50 : 75);
    };

    updateSizes();
    media.addEventListener("change", updateSizes);
    return () => media.removeEventListener("change", updateSizes);
  }, []);

    useEffect(() => {
        const wsUrl =
        (import.meta as any).env?.VITE_WS_URL || `ws://${window.location.hostname}:50000`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log('Connected to WebSocket server:', wsUrl)
            setIsConnected(true)
        }

        ws.onmessage = (event) => {
          let parsed: unknown
          try {
            parsed = JSON.parse(event.data)
          } catch (error) {
            console.warn('Failed to parse WebSocket message:', error)
            return
          }

          const messages = Array.isArray(parsed) ? parsed : [parsed]
          for (const message of messages) {
            if (!message || typeof message !== 'object') {
              continue
            }
            const { id, payload } = message as {
              id?: string
              payload?: Record<string, unknown>
            }
            if (id !== 'telemetry' || !payload) {
              continue
            }

            const speedValue = payload.speed_kmh ?? payload.speedKmh ?? payload.speed
            if (typeof speedValue === 'number' && Number.isFinite(speedValue)) {
              setSpeed(speedValue)
            }

            const distanceValue = payload.distance_cm ?? payload.distanceCm ?? payload.distance
            if (typeof distanceValue === 'number' && Number.isFinite(distanceValue)) {
              if (distanceValue === 1000) {
                setDistanceCm(null)
              }else {
                setDistanceCm(distanceValue)
              }
            }

            const emergencyValue =
              payload.emergency_stop_active ?? payload.emergencyStopActive ?? payload.emergency
            if (typeof emergencyValue === 'boolean') {
              setEmergencyStopActive(emergencyValue)
            }
          }
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
        <Joystick key={joystickKey} size={joystickSize} sticky={true} baseColor="rgba(171, 163, 163, 0.14)" stickColor="rgb(178, 35, 35)" stickSize={joystickStickSize} move={handleMove} stop={handleStop}></Joystick>
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
      
      <div className="flex flex-col items-center justify-center gap-4">
        <button className="p-4 bg-red-600 rounded-2xl text-white" onClick={() => toggleAutopilot()}>
          Mode
        </button>
        <p>{autopilotEnabled.current ? "Autopilot" : "Manual"}</p>
        <p>Geschwindigkeit: {speed.toFixed(2)} km/h</p>
        <p>Distanz: {distanceCm === null ? "-" : `${distanceCm.toFixed(1)} cm`}</p>
        <p>Notstopp: {emergencyStopActive ? "aktiv" : "aus"}</p>
      </div>
    </div>
  );
}