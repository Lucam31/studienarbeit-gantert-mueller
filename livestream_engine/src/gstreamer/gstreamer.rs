pub fn execute_gstreamer() {
    gst::init().unwrap();

    // Verbesserte Pipeline mit expliziten Caps und queue-Elementen
    let pipeline = gst::parse::launch(
        "libcamerasrc ! \
         video/x-raw,format=NV12 ! \
         videoscale ! \
         video/x-raw,width=1280,height=720 ! \
         videoconvert ! \
         queue max-size-buffers=1 leaky=downstream ! \
         x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast key-int-max=30 ! \
         video/x-h264,profile=baseline ! \
         h264parse config-interval=1 ! \
         mpegtsmux ! \
         hlssink location=segment%05d.ts playlist-location=playlist.m3u8 max-files=5 target-duration=2"
    ).expect("Pipeline konnte nicht erstellt werden");

    let pipeline = pipeline.dynamic_cast::<gst::Pipeline>().unwrap();

    pipeline.set_state(gst::State::Playing).expect("Konnte Pipeline nicht starten");

    println!("Streaming gestartet auf playlist.m3u8");

    let bus = pipeline.bus().unwrap();
    for msg in bus.iter_timed(gst::ClockTime::NONE) {
        use gst::MessageView;
        match msg.view() {
            MessageView::Eos(..) => {
                println!("Stream beendet");
                break;
            }
            MessageView::Error(err) => {
                eprintln!("Fehler: {:?}", err.error());
                eprintln!("Debug: {:?}", err.debug());
                break;
            }
            _ => (),
        }
    }

    pipeline.set_state(gst::State::Null).unwrap();
}