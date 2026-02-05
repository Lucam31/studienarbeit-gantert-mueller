use axum::{
    Router,
    response::{Response, IntoResponse},
    extract::State,
    http::{header, StatusCode},
};
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;
use std::sync::Arc;

#[tokio::main]
async fn main() {
    let camera = Arc::new(CameraStream::new(2));
    camera.start().await;

    let app = Router::new()
        .route("/stream", axum::routing::get(stream_handler))
        .with_state(camera);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn stream_handler(State(camera): State<Arc<CameraStream>>) -> Response {
    let rx = camera.subscribe();
    let stream = BroadcastStream::new(rx);

    let body = axum::body::Body::from_stream(
        stream.filter_map(|result| {
            result.ok().map(|data| {
                let boundary = "--frame\r\n";
                let header = format!(
                    "Content-Type: image/jpeg\r\nContent-Length: {}\r\n\r\n",
                    data.len()
                );

                let mut frame = Vec::new();
                frame.extend_from_slice(boundary.as_bytes());
                frame.extend_from_slice(header.as_bytes());
                frame.extend_from_slice(&data);
                frame.extend_from_slice(b"\r\n");

                Ok::<_, std::io::Error>(frame)
            })
        })
    );

    Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "multipart/x-mixed-replace; boundary=frame")
        .body(body)
        .unwrap()
}