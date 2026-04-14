def detection_capabilities():
    """Describe the simple detection stack used in this demo application."""
    return {
        "face_detection": "OpenCV Haarcascade or DNN face detector",
        "gaze_tracking": "MediaPipe face mesh landmarks",
        "object_detection": "Pretrained CNN or YOLO model connected later",
        "audio_monitoring": "Energy-based threshold logic in browser or backend worker",
    }


def kaggle_dataset_notes():
    """Provide dataset suggestions for future model improvement."""
    return [
        "Kaggle object detection datasets for phone and book recognition",
        "Face and gaze datasets for attention estimation",
        "Synthetic anti-cheating samples to test rule thresholds",
    ]
