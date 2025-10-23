from datetime import datetime, timezone, timedelta
import os
import cv2
from ultralytics import YOLO
import schedule
import requests
from dotenv import load_dotenv
import time
import threading

from detection.rest import ResourceService
from utils.opsw_logger import OpswLogger
from dependency_injector import providers

class PeopleCount(threading.Thread):
    # logger = providers.Singleton(OpswLogger)

    resourceSrv = providers.Singleton(ResourceService)
    resourceSrv().initialization()
    def __init__(self, thread_id, camera_indx = None):
        super(PeopleCount, self).__init__()
        self.thread_id = thread_id
        self.camera_index = camera_indx
        self.logger = OpswLogger(f"thread_{thread_id}")
        self.logger.initialization()
        # self.busId = None
        # self.busCapacity = None
        self.passengers = 0
        self.stop_event = threading.Event()
        self._finished = False
        # self.routeId = None

    # def loadEnviroment(self):
    #     # Main procedure of project
    #     # Load Application Properties
    #     load_dotenv()
    #     self.logger.logger.info("Enviroment loaded successfully.")
    #     # self.busId = os.getenv("bus.id")
    #     # if self.busId == None:
    #     #     raise Exception("Δεν έχει οριστεί κωδικός λεοφωρείου.")
    #     # busCapacitryStr = os.getenv("bus.capacity")
    #     # if busCapacitryStr == None:
    #     #     raise Exception("Δεν έχει ορισθεί χωρητικότητα λεοφωρείου.")
    #     # self.busCapacity = self.strToInt(busCapacitryStr)

    #     # Δεν χρειάζεται εδώ. Θα το ξέρει το Container το routeId που θα κάνει 
    #     # request στο Server.
    #     # routeIdStr = os.getenv("route.id")
    #     # if routeIdStr == None:
    #     #     raise Exception("Δεν έχει ορισθεί κωδικός διαδρομής λεοφωρείου.")
    #     # self.routeId = self.strToInt(routeIdStr)
    
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
    
    def updateCapacity(self):
        tz = timezone(timedelta(hours=3))
        self.resourceSrv().postCapacity(self.routeId, self.busId, self.busSenu, self.busCapacity, self.passengers, datetime.now(tz))

    def run(self):
        # self.loadEnviroment()
        # perform some action
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


        last_post = time.time()
        post_interval = 30  # seconds

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

        cap = cv2.VideoCapture(self.camera_index)
        widthFrame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        heightFrame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while True:
            if self.stop_event.is_set():
                break
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
                    if prev_x > line_position - offset > curr_x:
                        out_count += 1
                        print(f"Person {obj_id} entered")
                    elif prev_x < line_position + offset < curr_x:
                        in_count += 1
                        print(f"Person {obj_id} exited")

                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            cv2.line(frame, (line_position, 0), (line_position, frame.shape[0]), (255, 0, 0), 2)
            cv2.putText(frame, f'IN: {in_count}', (widthFrame - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
            cv2.putText(frame, f'OUT: {out_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)

            cv2.putText(frame, f'ID: {self.busId}', (10, heightFrame - 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
            cv2.putText(frame, f'CAP: {self.busCapacity}', (10, heightFrame - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
            tempCap = in_count - out_count
            if tempCap <= 0 :
                self.passengers = 0
            else:
                self.passengers = tempCap
            #Add Text in Frame about bus Capacity
            cv2.putText(frame, f'Passenger: {self.passengers}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 1)

            # Check if it's time to post data on backend
            if time.time() - last_post >= post_interval:
                thread = threading.Thread(target=self.updateCapacity)
                thread.start()
                # self.updateCapacity()
                last_post = time.time()


            #Create the Window with frames
            cv2.imshow("Passenger Counter", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.stop_event.set()
                break
