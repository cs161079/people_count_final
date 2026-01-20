from collections import defaultdict
import threading

import cv2
from ultralytics import YOLO
import detection.peopleCount02 as pc02


class PeopleCount04(pc02.PeopleCount02):
    def __init__(self, thread_id, stpEvent: threading.Event = None):
        super(PeopleCount04, self).__init__(thread_id=thread_id, stpEvent=stpEvent)
        self.filename = f"sample_5.mp4"
        print(f"PeopleCount Thread {self.thread_id} initialized.")
        self.passengersCount = 0
        self.initial_passengers = 25


    # Θέλω αν φτιάξω μία μέθοδο την οποία κάθε απόγωνος θα την υλοποιεί με βάση το βίντεο.
    def internal_run(self):

        return

    def run(self):
        # 1. Φόρτωση του μοντέλου YOLOv8 (το 'n' είναι η πιο γρήγορη έκδοση)
        # Την πρώτη φορά που θα τρέξει, θα κατεβάσει αυτόματα το αρχείο yolov8n.pt
        model = YOLO('yolov8n.pt')

        # 2. Άνοιγμα Κάμερας (0 για την προεπιλεγμένη webcam)
        # cap = cv2.VideoCapture(0)
        cap = cv2.VideoCapture(self.filename)  # Μπορείτε να βάλετε και διαδρομή αρχείου βίντεο
        
        # Ρύθμιση ανάλυσης (προαιρετικά, για ταχύτητα)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print("Σφάλμα: Η κάμερα δεν βρέθηκε.")
            return

        # --- Μεταβλητές Μέτρησης ---
        track_history = defaultdict(lambda: []) # Αποθηκεύει τη διαδρομή κάθε ID
        
        count_in = 0
        count_out = 0

        # Θέση της γραμμής (θα ρυθμιστεί δυναμικά μέσα στο loop)
        line_y = 0 

        print("Ξεκινάει η καταμέτρηση... Πατήστε 'q' για έξοδο.")

        def get_side(x, y, p1, p2):
            """
            Επιστρέφει > 0 αν το σημείο είναι από τη μία πλευρά, 
            και < 0 αν είναι από την άλλη.
            """
            return (p2[0] - p1[0]) * (y - p1[1]) - (p2[1] - p1[1]) * (x - p1[0])

        while not self.stop_event.is_set():
            success, frame = cap.read()
            if not success:
                print("Τέλος βίντεο ή σφάλμα ανάγνωσης.")
                break

            # Λήψη διαστάσεων εικόνας
            height, width, _ = frame.shape
            
            # Ορίζουμε τη γραμμή στη μέση της οθόνης (κάθετα)
            # line_x = int(width // 2)

            lineCoords = [(700, 1050), (1200, 550)]
            # 3. Εκτέλεση Tracking με YOLOv8
            # persist=True: Κρατάει τα IDs σταθερά μεταξύ των frames
            # classes=0: Ανιχνεύει μόνο ανθρώπους (class 0 στο COCO dataset)
            # tracker="bytetrack.yaml": Ένας γρήγορος αλγόριθμος tracking
            results = model.track(frame, persist=True, classes=0, verbose=False, tracker="bytetrack.yaml")

            # Αν υπάρχουν ανιχνεύσεις
            if results[0].boxes.id is not None:
                # Παίρνουμε τα κουτιά (x, y, w, h) και τα IDs
                boxes = results[0].boxes.xyxy.cpu().numpy()
                boxes02 = results[0].boxes.xywh.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                confidences = results[0].boxes.conf.cpu().numpy()

                previous_side = {}
                for box, box02, track_id, conf in zip(boxes, boxes02, track_ids, confidences):
                    # if conf < 0.5:
                    #     continue
                    x1, y1, x2, y2 = box
                    x, y, w, h = box02
                    
                    # Χρησιμοποιούμε το κέντρο της βάσης (πόδια) για ακρίβεια
                    cx = int((x1 + x2) / 2)
                    cy = int(y2) 

                    # Υπολογισμός πλευράς
                    current_side_val = get_side(cx, cy, lineCoords[0], lineCoords[1])
                    current_side = "inside" if current_side_val < 0 else "outside"

                    if track_id in track_history:
                        prev_side = track_history[track_id]
                        
                        # Έλεγχος αν πέρασε τη γραμμή
                        if prev_side == "outside" and current_side == "inside":
                            count_in += 1
                            cv2.line(frame, lineCoords[0], lineCoords[1], (0, 255, 0), 5)
                        elif prev_side == "inside" and current_side == "outside":
                            count_out += 1
                            cv2.line(frame, lineCoords[0], lineCoords[1], (0, 0, 255), 5)
                    
                    track_history[track_id] = current_side

                    # Σχεδίαση κύκλου στα πόδια του ατόμου
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    # Σχεδίαση κουτιού και ID γύρω από τον άνθρωπο
                    top_left_x = int(x - w / 2)
                    top_left_y = int(y - h / 2)
                    bottom_right_x = int(x + w / 2)
                    bottom_right_y = int(y + h / 2)
                    cv2.rectangle(frame, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (255, 255, 0), 2)
                    cv2.putText(frame, f"ID: {track_id}", (top_left_x, top_left_y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            # 4. Σχεδίαση γραφικών (UI)
            
            # Η γραμμή ελέγχου (Μπλε)                       B   G R 
            cv2.line(frame, lineCoords[0], lineCoords[1], (255, 0, 0), 2)
            # cv2.line(frame, (lineCoords[0][0], max_y), (lineCoords[1][0], max_y), (0, 255, 0), 2)
            # cv2.line(frame, (lineCoords[0][0], min_y), (lineCoords[1][0], min_y), (0, 255, 0), 2)
            
            # Πίνακας αποτελεσμάτων
            cv2.putText(frame, f"INITIAL: {self.initial_passengers}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            cv2.putText(frame, f"IN: {count_in}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"OUT: {count_out}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            self.passengersCount = max(0, self.initial_passengers + (count_in - count_out))
            cv2.putText(frame, f"Total: {self.passengersCount}", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

            # Εμφάνιση
            # cv2.imshow(self.window_name, frame)

            # Έξοδος με 'q'
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     # self.stop_event.set()
            #     break

        # Καθαρισμός
        cap.release()
        # cv2.destroyWindow(self.window_name)
        self._finished = True