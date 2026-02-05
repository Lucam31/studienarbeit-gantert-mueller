use crate::stream::capture::send_to_frontend;

mod stream;

fn main() {
    println!("Livestream");
    let mut capture = stream::capture::H264Capture::new(1280, 720);
    let mut buf = [0u8; 4096];

    loop {
        match capture.read_frame(&mut buf) {
            Ok(n) if n > 0 => {
                println!("Frame gelesen: {} Bytes", n);  // Debug-Print
                send_to_frontend(&buf[..n]);
            }
            Ok(_) => break,  // EOF
            Err(e) => eprintln!("Fehler beim Lesen: {}", e),  // Fehler-Print
        }
    }
}