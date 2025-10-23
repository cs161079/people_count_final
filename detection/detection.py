import cv2
from ultralytics import YOLO
import schedule

def fetch_data():
    url = "https://example.com/api/data"
    try:
        r = requests.get(url)
        print(f"{r.status_code}: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

def detection_count_passenger():

    # Line position
    line_position = 300
    offset = 10  # Tolerance to avoid multiple counts

    in_count = 0
    out_count = 0
    trackers = {}  # id: [previous_x, current_x]

    model = YOLO("yolov8n.pt")

    
    # Schedule to run every 10 seconds
    schedule.every(10).seconds.do(fetch_data)

    # Dummy function for person detection (replace with YOLO/dnn)
    def detect_people(frame):
        resultBoxes = []
        # Return list of bounding boxes [x, y, w, h]
        results = model(frame)
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                if model.names[cls] == 'person':
                    # x1, y1, x2, y2 = map(int, box.xyxy[0])
                    obId = box.id
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    resultBoxes.append((x1, y1, x2, y2))
        return resultBoxes

    # Dummy function for tracking
    def track_objects(detections):
        # Return dict: id -> centroid
        return {i: (int((x+w)/2), int((y+h)/2)) for i, (x, y, w, h) in enumerate(detections)}

    cap = cv2.VideoCapture(0)
    widthFrame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = detect_people(frame)
        objects = track_objects(detections)

        for obj_id, (cx, cy) in objects.items():
            if obj_id not in trackers:
                trackers[obj_id] = [cx, cx]
            else:
                trackers[obj_id][0] = trackers[obj_id][1]
                trackers[obj_id][1] = cx

                prev_x, curr_x = trackers[obj_id]
                if prev_x < line_position - offset < curr_x:
                    in_count += 1
                    print(f"Person {obj_id} entered")
                elif prev_x > line_position + offset > curr_x:
                    out_count += 1
                    print(f"Person {obj_id} exited")

            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        cv2.line(frame, (line_position, 0), (line_position, frame.shape[0]), (255, 0, 0), 2)
        cv2.putText(frame, f'IN: {in_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
        cv2.putText(frame, f'OUT: {out_count}', (widthFrame - 60, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
        cv2.putText(frame, f'Passenger: {abs(out_count-in_count)}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)


        cv2.imshow("Passenger Counter", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break