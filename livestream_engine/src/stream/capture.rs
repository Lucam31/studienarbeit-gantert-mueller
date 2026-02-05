use std::io::Write;
use std::fs::OpenOptions;
use std::io::Read;
use std::process::{Command, Stdio};

pub struct H264Capture {
    child: std::process::Child,
    stdout: std::process::ChildStdout,
}

impl H264Capture {
    pub fn new(width: u32, height: u32) -> Self {
        let mut child = Command::new("rpicam-vid")
            .args([
                "-t", "0",
                "--width", &width.to_string(),
                "--height", &height.to_string(),
                "--codec", "h264",
                "--inline",
                "-o", "-.h264"
            ])
            .stdout(Stdio::piped())
            .spawn()
            .expect("rpicam-vid nicht gefunden");

        let stdout = child.stdout.take().unwrap();

        Self { child, stdout }
    }

    pub fn read_frame(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
        self.stdout.read(buffer)
    }
}

impl Drop for H264Capture {
    fn drop(&mut self) {
        let _ = self.child.kill();
    }
}

pub fn send_to_frontend(_data: &[u8]) {
    println!("send to frontend");
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open("/tmp/h264_stream.h264")
        .expect("Datei konnte nicht geöffnet werden");
    file.write_all(_data).expect("Schreiben fehlgeschlagen");

}
