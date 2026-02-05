use tokio::sync::broadcast;
use tokio::time::{interval, Duration};
use image::{ImageBuffer, RgbImage};
use std::sync::Arc;

pub struct CameraStream {
    tx: broadcast::Sender<Arc<Vec<u8>>>,
}

impl CameraStream {
    pub fn new(capacity: usize) -> Self {
        let (tx, _) = broadcast::channel(capacity);
        Self { tx }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<Arc<Vec<u8>>> {
        self.tx.subscribe()
    }

    pub async fn start(&self) {
        let tx = self.tx.clone();

        tokio::spawn(async move {
            let mut ticker = interval(Duration::from_millis(33)); // ~30 FPS

            loop {
                ticker.tick().await;

                // Hier Bild von der Kamera holen (z.B. mit rascam oder v4l)
                let frame = capture_frame().await;

                // Als JPEG encodieren
                if let Ok(jpeg_data) = encode_jpeg(&frame) {
                    let _ = tx.send(Arc::new(jpeg_data));
                }
            }
        });
    }
}

async fn capture_frame() -> RgbImage {
    // TODO: Echte Kamera-Integration (rascam, v4l2, etc.)
    ImageBuffer::new(640, 480)
}

fn encode_jpeg(img: &RgbImage) -> Result<Vec<u8>, image::ImageError> {
    let mut buffer = Vec::new();
    let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut buffer, 85);
    encoder.encode_image(img)?;
    Ok(buffer)
}