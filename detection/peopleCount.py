import cv2
from ultralytics import YOLO
import schedule
import time
import threading

from detection.rest import ResourceService
from utils.opsw_logger import OpswLogger
from dependency_injector import providers

class PeopleCount(threading.Thread):
    # logger = providers.Singleton(OpswLogger)

    resourceSrv = providers.Singleton(ResourceService)
    resourceSrv().initialization()
    def __init__(self, thread_id, camera_indx = None, bus_id = None, bus_capacity = None, stpEvent: threading.Event = None):
        super(PeopleCount, self).__init__()
        self.bus_id = bus_id
        self.bus_capacity = bus_capacity
        self.thread_id = thread_id
        self.camera_index = camera_indx
        self.logger = OpswLogger(f"thread_{thread_id}")
        self.logger.initialization()
        self.window_name =f"PeopleCount Thread {self.thread_id}"
        self.passengers = 0
        self.stop_event = stpEvent
        self._finished = False
        print(f"PeopleCount Thread {self.thread_id} initialized.")
    
    def getPassengers(self):
        # print(f"Thread {self.thread_id} current passengers are {self.passengers}")
        self.logger.logger.info(f"Thread {self.thread_id} current passengers are {self.passengers}")
        return self.passengers

    def thread_finished(self):
        # print(f"Thread {self.thread_id} finished -> {self._finished}")
        return self._finished
    
    def stop(self):
        self.stop_event.set()

    def strToInt(self, strVal):
        try:
            i = int(strVal)
        except ValueError:
            self.logger.logger.error(f"Not a valid integer value.[{strVal}]")
        return i

    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def run(self):
        # self.loadEnviroment()
        # perform some action
        if self.bus_id is None:
            print("Bus ID is not provided. Exiting thread.")
            return
        self.logger.logger.info("People count process started.")
        self.__peopleCount()
    
    # 🔒 Private method that load yolov8n model to detect objects in frames
    def __peopleCount(self):        
        line_position = 300
        offset = 10  # Tolerance to avoid multiple counts

        in_count = 0
        out_count = 0
        trackers = {}  # id: [previous_x, current_x]

        model = YOLO("yolov8n.pt")


        # last_post = time.time()
        # post_interval = 30  # seconds

        # Dummy function for person detection (replace with YOLO/dnn)
        def detect_people(frame):
            resultBoxes = []
            # Return list of bounding boxes [x, y, w, h]
            results = model(frame, verbose=False)
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

        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"Error: Could not open camera with index {self.camera_index}")
            return
        widthFrame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        heightFrame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while True:
            if self.stop_event.is_set():
                break
            ret, frame = cap.read()
            if not ret:
                print("Error: Δεν μπόρεσα να διαβάσω frame (Video ended or Camera disconnected).")
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
                    if prev_x > line_position - offset > curr_x:
                        out_count += 1
                        print(f"Person {obj_id} entered")
                    elif prev_x < line_position + offset < curr_x:
                        in_count += 1
                        print(f"Person {obj_id} exited")

                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            cv2.line(frame, (line_position, 0), (line_position, frame.shape[0]), (255, 0, 0), 2)


            # Πίνακας αποτελεσμάτων
            cv2.putText(frame, f'IN: {in_count}', (widthFrame - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            cv2.putText(frame, f'OUT: {out_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)


            
            cv2.putText(frame, f'ID: {self.bus_id}', (10, heightFrame - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            cv2.putText(frame, f'CAP: {self.bus_capacity}', (10, heightFrame - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            self.passengers = in_count - out_count
            #Add Text in Frame about bus Capacity
            cv2.putText(frame, f'Passenger: {self.passengers}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

            cv2.imshow(self.window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.stop_event.set()
                break
        # Καθαρισμός
        cap.release()
        cv2.destroyWindow(self.window_name)
        self._finished = True
