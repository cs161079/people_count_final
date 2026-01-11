import cv2
from ultralytics import YOLO
from collections import defaultdict

def count_passengers():
    # 1. Φόρτωση του μοντέλου YOLOv8 (το 'n' είναι η πιο γρήγορη έκδοση)
    # Την πρώτη φορά που θα τρέξει, θα κατεβάσει αυτόματα το αρχείο yolov8n.pt
    model = YOLO('yolov8n.pt')

    # 2. Άνοιγμα Κάμερας (0 για την προεπιλεγμένη webcam)
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture("sample_1.mp4")  # Μπορείτε να βάλετε και διαδρομή αρχείου βίντεο
    
    # Ρύθμιση ανάλυσης (προαιρετικά, για ταχύτητα)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Σφάλμα: Η κάμερα δεν βρέθηκε.")
        return

    # --- Μεταβλητές Μέτρησης ---
    track_history = defaultdict(lambda: []) # Αποθηκεύει τη διαδρομή κάθε ID
    entered_ids = set() # IDs που έχουν ήδη μετρηθεί ως είσοδος
    exited_ids = set()  # IDs που έχουν ήδη μετρηθεί ως έξοδος
    
    count_in = 0
    count_out = 0

    # Θέση της γραμμής (θα ρυθμιστεί δυναμικά μέσα στο loop)
    line_y = 0 

    print("Ξεκινάει η καταμέτρηση... Πατήστε 'q' για έξοδο.")

    while True:
        success, frame = cap.read()
        if not success:
            print("Τέλος βίντεο ή σφάλμα ανάγνωσης.")
            break

        # Λήψη διαστάσεων εικόνας
        height, width, _ = frame.shape
        
        # Ορίζουμε τη γραμμή στη μέση της οθόνης (κάθετα)
        line_y = int(height // 2) + 200

        # 3. Εκτέλεση Tracking με YOLOv8
        # persist=True: Κρατάει τα IDs σταθερά μεταξύ των frames
        # classes=0: Ανιχνεύει μόνο ανθρώπους (class 0 στο COCO dataset)
        # tracker="bytetrack.yaml": Ένας γρήγορος αλγόριθμος tracking
        results = model.track(frame, persist=True, classes=0, verbose=False, tracker="bytetrack.yaml")

        # Αν υπάρχουν ανιχνεύσεις
        if results[0].boxes.id is not None:
            # Παίρνουμε τα κουτιά (x, y, w, h) και τα IDs
            boxes = results[0].boxes.xywh.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()

            for box, track_id in zip(boxes, track_ids):
                x, y, w, h = box
                
                # Υπολογισμός κέντρου του ανθρώπου
                center_x = float(x)
                center_y = float(y)

                # Αποθήκευση ιστορικού κίνησης
                track = track_history[track_id]
                track.append((center_x, center_y))
                
                # Κρατάμε μόνο τα τελευταία 30 σημεία για να μην γεμίζει η μνήμη
                if len(track) > 30:
                    track.pop(0)

                curr_x, curr_y = [None, None]
                # --- ΛΟΓΙΚΗ ΜΕΤΡΗΣΗΣ ---
                # Χρειαζόμαστε τουλάχιστον 2 καρέ για να δούμε κίνηση
                if len(track) > 2:
                    prev_y = track[-2][1] # Η προηγούμενη θέση Y
                    # curr_x = track[-1][1] # Η τωρινή θέση Y
                    curr_x, curr_y = track[-1]

                    # Έλεγχος: Διασχίζει τη γραμμή προς τα ΚΑΤΩ (Είσοδος)
                    if prev_y < line_y and curr_y >= line_y:
                        if track_id not in entered_ids:
                            count_out += 1
                            entered_ids.add(track_id)
                            # Ζωγραφίζουμε πράσινη γραμμή ένδειξης
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

        # 4. Σχεδίαση γραφικών (UI)
        
        # Η γραμμή ελέγχου (Μπλε)
        cv2.line(frame, (0, line_y), (width, line_y), (255, 0, 0), 2)
        
        # Πίνακας αποτελεσμάτων
        cv2.putText(frame, f"IN: {count_in}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"OUT: {count_out}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        total_passengers = max(0, count_in - count_out)
        cv2.putText(frame, f"Total: {total_passengers}", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Εμφάνιση
        cv2.imshow("Bus Passenger Counter", frame)

        # Έξοδος με 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Καθαρισμός
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    count_passengers()