export class WebRTCReader {
  private pc: RTCPeerConnection;
  private url: string;
  private onTrack?: (evt: RTCTrackEvent) => void;
  private onError?: (err: Error) => void;

  constructor(config: {
    url: string;
    onTrack?: (evt: RTCTrackEvent) => void;
    onError?: (err: Error) => void;
  }) {
    this.url = config.url;
    this.onTrack = config.onTrack;
    this.onError = config.onError;
    
    this.pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    this.pc.ontrack = (evt) => {
      console.log("Track received:", evt);
      this.onTrack?.(evt);
    };

    this.pc.oniceconnectionstatechange = () => {
      console.log("ICE connection state:", this.pc.iceConnectionState);
    };

    this.start();
  }

  private async start() {
    try {
      // Transceiver für Video hinzufügen
      this.pc.addTransceiver("video", { direction: "recvonly" });
      this.pc.addTransceiver("audio", { direction: "recvonly" });

      // Offer erstellen
      const offer = await this.pc.createOffer();
      await this.pc.setLocalDescription(offer);

      // WHEP Request an MediaMTX
      const response = await fetch(this.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/sdp",
        },
        body: offer.sdp,
      });

      if (!response.ok) {
        throw new Error(`WHEP request failed: ${response.status}`);
      }

      const answerSdp = await response.text();
      await this.pc.setRemoteDescription({
        type: "answer",
        sdp: answerSdp,
      });

      console.log("WebRTC connection established");
    } catch (err) {
      console.error("WebRTC setup error:", err);
      this.onError?.(err as Error);
    }
  }

  close() {
    this.pc.close();
  }
}