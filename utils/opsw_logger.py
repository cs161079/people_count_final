import logging
import os

class OpswLogger:
    def __init__(self, thread_name: str = "main_thread"):
        self.thread_name = thread_name
        self.logger = logging.getLogger(self.thread_name)

    def initialization(self):
        self.logger.setLevel(logging.DEBUG) 
       # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(formatter)
        # if fileName == None:
        #     fileName = "app.log"
        fileName = f"{self.thread_name}.log"
        
        # Define folder and file paths
        log_folder = "logs"
        log_file = os.path.join(log_folder, fileName)

        # Create the folder if it doesn't exist
        os.makedirs(log_folder, exist_ok=True)
        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        # Create formatter and add to handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)