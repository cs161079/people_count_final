from collections import defaultdict
import cv2
from ultralytics import YOLO
import threading

class PeopleCount02(threading.Thread):
    ...
    def __init__(self, thread_id, stpEvent: threading.Event = None, filename: str = "sample_1.mp4"):
        super(PeopleCount02, self).__init__()
        self.passengersCount = 0
        self.thread_id = thread_id
        self.stop_event = stpEvent
        self.window_name = f"PeopleCount Thread {self.thread_id}"
        self._finished = False
        self.filename = filename
        print(f"PeopleCount Thread {self.thread_id} initialized.")

    def getPassengers(self):
        return self.passengersCount
    
    def thread_finished(self):
        return self._finished
    
    def run(self):
        model = YOLO('yolov8n.pt')
        cap = cv2.VideoCapture(self.filename)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print("Σφάλμα: Η κάμερα δεν βρέθηκε.")
            return

        track_history = defaultdict(lambda: [])
        # IDs που έχουν ήδη μετρηθεί ως είσοδος
        entered_ids = set()
        # IDs που έχουν ήδη μετρηθεί ως έξοδος
        exited_ids = set()
        
        count_in = 0
        count_out = 0

        # Θέση της γραμμής (θα ρυθμιστεί δυναμικά μέσα στο loop)
        line_y = 0 

        print("Ξεκινάει η καταμέτρηση... Πατήστε 'q' για έξοδο.")

        while not self.stop_event.is_set():
            success, frame = cap.read()
            if not success:
                print("Τέλος βίντεο ή σφάλμα ανάγνωσης.")
                break
            height, width, _ = frame.shape
            
            line_y = int(height // 2) + 200
            results = model.track(frame, persist=True, classes=0, verbose=False, tracker="bytetrack.yaml")

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()

                for box, track_id in zip(boxes, track_ids):
                    x, y, w, h = box
                    
                    center_x = float(x)
                    center_y = float(y)

                    track = track_history[track_id]
                    track.append((center_x, center_y))
                    
                    
                    if len(track) > 30:
                        track.pop(0)

                    curr_x, curr_y = [None, None]
                    if len(track) > 2:
                        prev_y = track[-2][1]
                        curr_x, curr_y = track[-1]

                        if prev_y < line_y and curr_y >= line_y:
                            if track_id not in entered_ids:
                                count_out += 1
                                entered_ids.add(track_id)
                                cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 0), 5)

                        # Έλεγχος: Διασχίζει τη γραμμή προς τα ΠΑΝΩ (Έξοδος)
                        elif prev_y > line_y and curr_y <= line_y:
                            if track_id not in exited_ids:
                                count_in += 1
                                exited_ids.add(track_id)
                                # Ζωγραφίζουμε κόκκινη γραμμή ένδειξης
                                cv2.line(frame, (0, line_y), (width, line_y), (0, 0, 255), 5)

                    # Σχεδίαση κουτιού και ID γύρω από τον άνθρωπο
                    top_left_x = int(x - w / 2)
                    top_left_y = int(y - h / 2)
                    bottom_right_x = int(x + w / 2)
                    bottom_right_y = int(y + h / 2)
                    
                    cv2.rectangle(frame, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (255, 255, 0), 2)
                    if curr_y is not None and curr_x is not None:
                        cv2.circle(frame, (int(curr_x), int(curr_y)), 3, (0, 255, 0), -1)
                    cv2.putText(frame, f"ID: {track_id}", (top_left_x, top_left_y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # Η γραμμή ελέγχου (Μπλε)
            cv2.line(frame, (0, line_y), (width, line_y), (255, 0, 0), 2)
            
            # Πίνακας αποτελεσμάτων
            cv2.putText(frame, f"IN: {count_in}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"OUT: {count_out}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            self.passengersCount = count_in - count_out
            cv2.putText(frame, f"Total: {self.passengersCount}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Εμφάνιση
            cv2.imshow(self.window_name, frame)

            # Έξοδος με 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                # self.stop_event.set()
                break

        # Καθαρισμός
        cap.release()
        cv2.destroyWindow(self.window_name)
        self._finished = True